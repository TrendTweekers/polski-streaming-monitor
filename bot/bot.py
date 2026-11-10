"""Daily streaming test bot.

For each enabled VPN provider: start a WireGuard tunnel in user space (wireproxy),
check that the exit IP is in Poland, then try real video playback on each enabled
service. Results and screenshots go to site/data/. Adding a provider or a service
is a change in config.json only.

Secrets (WireGuard configs) come from environment variables or, on a local run,
from bot/secrets/<ENV_NAME>.conf. They are never printed.
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent / "site"
DATA = SITE / "data"
CFG = json.loads((ROOT / "config.json").read_text())
PORT = 25344
PROXY = f"socks5://127.0.0.1:{PORT}"
WARSAW = dt.timezone(dt.timedelta(hours=1))  # CET; good enough for a timestamp label

CONSENT = ["Akceptuję", "Akceptuj wszystkie", "Zaakceptuj wszystko", "Zaakceptuj", "Zgadzam się", "Przejdź do serwisu", "Akceptuj"]
BLOCK_TEXTS = [
    (r"wykryto wtyczkę adblock|wyłącz blokowanie reklam", "Serwis pokazał komunikat o blokowaniu reklam"),
    (r"niedostępn\w+ w twoim kraju|poza granicami polski|tylko na terytorium|nie jest dostępn\w+ w twoim regionie|geoblok", "Serwis pokazał komunikat o blokadzie regionalnej"),
    (r"vpn lub proxy|wyłącz vpn|korzystasz z vpn", "Serwis wykrył VPN"),
]
VIDEO_JS = """()=>Array.from(document.querySelectorAll('video')).map(v=>({t:v.currentTime,paused:v.paused,w:v.videoWidth,h:v.videoHeight,drm:!!v.mediaKeys,src:(v.currentSrc||'')}))"""


def now():
    return dt.datetime.now(WARSAW)


def log(*a):
    print(now().strftime("%H:%M:%S"), *a, flush=True)


def fetch_json(url, proxy=False, timeout=25):
    cmd = ["curl", "-s", "--max-time", str(timeout)]
    if proxy:
        cmd += ["--socks5-hostname", f"127.0.0.1:{PORT}"]
    out = subprocess.run(cmd + [url], capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {}


def ensure_wireproxy():
    binp = ROOT / "bin" / "wireproxy"
    if binp.exists():
        return binp
    binp.parent.mkdir(exist_ok=True)
    tgz = binp.parent / "wp.tar.gz"
    urllib.request.urlretrieve(CFG["wireproxy"]["url"], tgz)
    digest = hashlib.sha256(tgz.read_bytes()).hexdigest()
    if digest != CFG["wireproxy"]["sha256"]:
        raise RuntimeError("wireproxy checksum mismatch")
    with tarfile.open(tgz) as t:
        t.extract("wireproxy", binp.parent)
    binp.chmod(0o755)
    return binp


def secret_for(env_name):
    val = os.environ.get(env_name)
    if val:
        return val
    f = ROOT / "secrets" / (env_name + ".conf")
    return f.read_text() if f.exists() else None


class Tunnel:
    def __init__(self, wg_conf):
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        conf = re.sub(r"(?m)^DNS\s*=.*$", "DNS = " + CFG["dns"], wg_conf.replace("\r", ""))
        (d / "wg.conf").write_text(conf)
        (d / "wg.conf").chmod(0o600)
        (d / "wp.conf").write_text(f"WGConfig = {d/'wg.conf'}\n\n[Socks5]\nBindAddress = 127.0.0.1:{PORT}\n")
        self.proc = subprocess.Popen([str(ensure_wireproxy()), "-c", str(d / "wp.conf")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4)

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except Exception:
            self.proc.kill()
        self.dir.cleanup()


def speed_mbps():
    """Download 20 MB through the tunnel, three times; return the mean in Mb/s."""
    vals = []
    for _ in range(3):
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "--max-time", "40", "--socks5-hostname", f"127.0.0.1:{PORT}",
                            "-w", "%{speed_download}", "https://speed.cloudflare.com/__down?bytes=20000000"], capture_output=True, text=True)
        try:
            v = float(r.stdout) * 8 / 1e6
            if v > 0.1:
                vals.append(v)
        except Exception:
            pass
    return round(sum(vals) / len(vals), 1) if vals else None


def videos(page):
    out = []
    for f in page.frames:
        try:
            out += f.evaluate(VIDEO_JS)
        except Exception:
            pass
    return out


def click_first(page, labels):
    for f in page.frames:
        for label in labels:
            try:
                f.get_by_role("button", name=label, exact=False).first.click(timeout=1200)
                return True
            except Exception:
                pass
    return False


def save_shot(page, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".png")
    page.screenshot(path=str(tmp))
    Image.open(tmp).convert("RGB").save(path, "WEBP", quality=72)
    tmp.unlink()


def test_service(browser, svc, shot_path):
    """Return a result dict. status: ok | unstable | blocked | none."""
    res = {"status": "none", "reason": None, "tested_at": now().isoformat(timespec="seconds")}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
    page = ctx.new_page()
    try:
        page.goto(svc["url"], wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(6000)
        click_first(page, CONSENT)
        page.wait_for_timeout(2500)
        loc = page.locator("a,button").filter(has_text=re.compile(svc["play"], re.I))
        cands = [e for e in loc.all() if e.is_visible() and (e.bounding_box() or {}).get("y", 0) > 100]
        if cands:
            cands[0].click(timeout=8000)
        t0 = time.time()
        start = None       # (wall time, video time) when the real programme began
        last = None
        shot_done = False
        ads_until = None
        while time.time() - t0 < CFG["max_wait_seconds"]:
            page.wait_for_timeout(5000)
            main = [v for v in videos(page) if v["src"].startswith("blob:") and v["w"] > 0]
            if main:
                v = max(main, key=lambda x: x["t"])
                if start is None and v["t"] > 0:
                    start = (time.time(), v["t"])
                    ads_until = round(time.time() - t0)
                last = v
                if start:
                    played = v["t"] - start[1]
                    if not shot_done and played >= 20:
                        save_shot(page, shot_path)
                        shot_done = True
                    if time.time() - start[0] >= CFG["watch_seconds"]:
                        break
            else:
                body = ""
                try:
                    body = page.evaluate("()=>document.body.innerText.slice(0,60000)")
                except Exception:
                    pass
                for pat, why in BLOCK_TEXTS:
                    if re.search(pat, body, re.I):
                        res.update(status="blocked", reason=why)
                        break
                if res["status"] == "blocked" and time.time() - t0 > 60:
                    break
        if start and last:
            played = round(last["t"] - start[1], 1)
            wall = time.time() - start[0]
            res.update(played_seconds=played, wait_seconds=ads_until, resolution=f'{last["w"]}x{last["h"]}', drm=last["drm"])
            if played >= CFG["watch_seconds"] - 8:
                res.update(status="ok", reason=None)
            elif played >= 3:
                res.update(status="unstable", reason=f"Film grał {int(played)} s w ciągu {int(wall)} s")
            else:
                res.update(status="blocked", reason="Film nie ruszył")
        elif res["status"] != "blocked":
            res.update(status="blocked", reason="Film nie ruszył w ciągu %d s" % CFG["max_wait_seconds"])
        if not shot_done:
            save_shot(page, shot_path)
        res["shot"] = str(shot_path.relative_to(SITE))
    except Exception as e:  # a bot fault is "not tested", never "blocked"
        res.update(status="none", reason="Błąd bota: " + type(e).__name__)
        log("  bot error:", type(e).__name__, str(e)[:160])
    finally:
        ctx.close()
    return res


def main():
    day = now().strftime("%Y-%m-%d")
    started = now()
    runner = fetch_json("https://ipinfo.io/json")
    run = {"date": day, "started_at": started.isoformat(timespec="seconds"),
           "runner": {"country": runner.get("country")},  # country only: a local run must not publish the owner's city
           "watch_seconds": CFG["watch_seconds"], "providers": [], "services": [
               {"id": s["id"], "name": s["name"], "enabled": s.get("enabled", False)} for s in CFG["services"]]}
    services = [s for s in CFG["services"] if s.get("enabled")]
    with sync_playwright() as p:
        for prov in CFG["providers"]:
            entry = {"id": prov["id"], "name": prov["name"], "plan": prov.get("plan"), "server": prov.get("server"),
                     "tested": False, "services": {}}
            run["providers"].append(entry)
            if not prov.get("enabled"):
                continue
            conf = secret_for(prov["secret_env"])
            if not conf:
                entry["note"] = "Brak konfiguracji VPN"
                log(prov["name"], "- no secret, skipped")
                continue
            log(prov["name"], "- connecting")
            tun = Tunnel(conf)
            try:
                ip = fetch_json("https://ipinfo.io/json", proxy=True)
                if ip.get("country") != "PL":
                    ip = fetch_json("https://ipinfo.io/json", proxy=True)
                if ip.get("country") != "PL":
                    entry["note"] = "Adres IP serwera VPN nie jest polski"
                    log("  exit IP is not Polish:", ip.get("country"))
                    continue
                parts = (ip.get("ip") or "").split(".")
                entry["exit"] = {"ip": ".".join(parts[:3] + ["x"]) if len(parts) == 4 else None,
                                 "city": ip.get("city"), "country": "PL", "org": ip.get("org")}
                log("  exit IP ok:", entry["exit"]["city"], entry["exit"]["org"])
                entry["speed_mbps"] = speed_mbps()
                log("  speed:", entry["speed_mbps"])
                browser = p.chromium.launch(headless=False, proxy={"server": PROXY}, executable_path=os.environ.get("BOT_CHROME") or None,
                                            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required", "--mute-audio"])
                try:
                    for svc in services:
                        log("  testing", svc["name"])
                        shot = DATA / "shots" / day / f'{prov["id"]}-{svc["id"]}.webp'
                        r = test_service(browser, svc, shot)
                        entry["services"][svc["id"]] = r
                        log("   ->", r["status"], r.get("reason") or "", r.get("played_seconds"))
                finally:
                    browser.close()
                entry["tested"] = any(r["status"] != "none" for r in entry["services"].values())
            finally:
                tun.close()
    run["finished_at"] = now().isoformat(timespec="seconds")

    tested = [e for e in run["providers"] if e["tested"]]
    if not tested:
        log("No provider was tested. Nothing published.")
        return 1
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(run, ensure_ascii=False, indent=1))
    hist_f = DATA / "history.json"
    hist = json.loads(hist_f.read_text()) if hist_f.exists() else {"days": {}}
    hist["days"][day] = {e["id"]: {k: v["status"] for k, v in e["services"].items()} for e in tested}
    hist["days"] = dict(sorted(hist["days"].items())[-90:])
    hist_f.write_text(json.dumps(hist, ensure_ascii=False, indent=1))
    # keep screenshots for 30 days
    keep = set(sorted(hist["days"])[-30:])
    for d in (DATA / "shots").iterdir():
        if d.is_dir() and d.name not in keep:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    log("Published", day)
    return 0


if __name__ == "__main__":
    sys.exit(main())
