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
BLOCK_TEXTS = [  # (pattern, reason on the site, kind). First match wins.
    (r"wykryto wtyczkę adblock|wyłącz blokowanie reklam", "Serwis pokazał komunikat o blokowaniu reklam", "adblock"),
    (r"niedostępn\w+ w twoim kraju|poza granicami polski|tylko na terytorium|nie jest dostępn\w+ w twoim regionie|geoblok", "Serwis pokazał komunikat o blokadzie regionalnej", "geo"),
    (r"vpn lub proxy|wyłącz vpn|korzystasz z vpn", "Serwis wykrył VPN", "vpn"),
    (r"wystąpił problem z materiałem|nie udało się odtworzyć|coś poszło nie tak", "Serwis pokazał błąd odtwarzania", "player"),
    (r"musisz się zalogować|zaloguj się, aby (oglądać|obejrzeć)", "Serwis wymagał logowania", "login"),
    (r"wykup dostęp|kup pakiet, aby oglądać|materiał dostępny w pakiecie", "Serwis wymagał płatnego pakietu", "paid"),
]
# Kinds that say nothing about the VPN: the result is "not tested", never "blocked".
NOT_VPN = {"login", "paid", "outage", "bot", "vpn_down"}
# Messages after which the bot reloads the page one time, as a viewer would.
RELOAD_ON = {"Serwis pokazał błąd odtwarzania", "Serwis pokazał komunikat o blokowaniu reklam"}
VIDEO_JS = """()=>Array.from(document.querySelectorAll('video')).map(v=>({t:v.currentTime,paused:v.paused,w:v.videoWidth,h:v.videoHeight,drm:!!v.mediaKeys,d:(isFinite(v.duration)?v.duration:0),src:(v.currentSrc||'')}))"""


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


def pia_conf():
    """PIA has no WireGuard file: build one for this run from the username and password."""
    user, pw = os.environ.get("PIA_USER"), os.environ.get("PIA_PASS")
    f = ROOT / "secrets" / "pia.env"
    if not (user and pw) and f.exists():
        kv = dict(l.split("=", 1) for l in f.read_text().splitlines() if "=" in l)
        user, pw = kv.get("PIA_USER"), kv.get("PIA_PASS")
    if not (user and pw):
        return None
    try:
        import pia
        return pia.make_conf(user, pw)
    except Exception as e:
        log("  PIA config failed:", type(e).__name__)
        return None


class OvpnTunnel:
    """OpenVPN in a small Docker container (bot/ovpn) that offers the same SOCKS5 port as wireproxy.
    conf is 'OVPN_TEXT\x00AUTH_TEXT'. Needs Docker (GitHub runner)."""
    IMAGE = "ps-ovpn"

    def __init__(self, conf):
        ovpn, auth = conf.split("\x00", 1)
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        (d / "client.ovpn").write_text(ovpn.replace("\r", ""))
        (d / "auth.txt").write_text(auth.replace("\r", ""))
        os.chmod(d, 0o755)
        for f in ("client.ovpn", "auth.txt"):
            (d / f).chmod(0o644)
        if subprocess.run(["docker", "image", "inspect", self.IMAGE], capture_output=True).returncode != 0:
            b = subprocess.run(["docker", "build", "-t", self.IMAGE, str(ROOT / "ovpn")], capture_output=True, text=True)
            if b.returncode != 0:
                log("  docker build failed:", (b.stdout + b.stderr)[-1500:])
                raise RuntimeError("docker build failed")
        self.name = f"psovpn{os.getpid()}{int(time.time()) % 100000}"
        subprocess.run(["docker", "run", "-d", "--rm", "--name", self.name, "--cap-add=NET_ADMIN", "--device", "/dev/net/tun",
                        "-e", "DNS=" + CFG["dns"], "-p", f"127.0.0.1:{PORT}:1080", "-v", f"{d}:/vpn:ro", self.IMAGE],
                       check=True, capture_output=True)
        for _ in range(45):
            out = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
            if "vpn up" in out.stdout:
                break
            if "did not come up" in out.stdout:
                log("  openvpn failed:", out.stdout[-400:])
                break
            time.sleep(1)
        time.sleep(2)

    def close(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        self.dir.cleanup()


def make_tunnel(conf):
    return OvpnTunnel(conf) if "\x00" in conf else Tunnel(conf)


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


def listing_urls(page, svc):
    """Open a listing page and return the video page links on it (newest first)."""
    page.goto(svc["listing"], wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    click_first(page, CONSENT)
    page.wait_for_timeout(1500)
    hrefs = page.eval_on_selector_all("a[href]", "els=>els.map(e=>e.href)")
    out = []
    for h in hrefs:
        if re.search(svc["listing_link"], h) and h not in out:
            out.append(h)
    return out


def start_playback(page, svc):
    if svc.get("play_selector"):
        for f in page.frames:
            try:
                e = f.locator(svc["play_selector"]).first
                if e.is_visible():
                    e.click(timeout=3000)
                    return
            except Exception:
                pass
        return
    loc = page.locator("a,button").filter(has_text=re.compile(svc["play"], re.I))
    cands = [e for e in loc.all() if e.is_visible() and (e.bounding_box() or {}).get("y", 0) > 100]
    if cands:
        cands[0].click(timeout=8000)


def long_enough(page):
    """For clips picked from a listing: is the clip long enough for the 60 s check?"""
    # An advert plays first and is short, so a short video alone proves nothing.
    # Wait up to 100 s for a video that is long enough (the clip after the advert).
    for _ in range(20):
        page.wait_for_timeout(5000)
        ds = [v["d"] for v in videos(page) if v["src"].startswith("blob:") and v["d"] > 0]
        if ds and max(ds) >= CFG["watch_seconds"] + 20:
            return True
        try:  # the player shows its own error for this clip: take the next clip
            if re.search(r"coś poszło nie tak", page.evaluate("()=>document.body.innerText.slice(0,60000)"), re.I):
                return False
        except Exception:
            pass
    return False  # only short videos, or no playable video, on this clip page


CLIP = {}  # service id -> clip page that was long enough earlier in this run


def test_service(browser, svc, shot_path):
    """Return a result dict. status: ok | unstable | blocked | none."""
    res = {"status": "none", "reason": None, "tested_at": now().isoformat(timespec="seconds")}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
    page = ctx.new_page()
    try:
        cached = CLIP.get(svc["id"]) if svc.get("listing") else None
        urls = [cached] if cached else (listing_urls(page, svc) if svc.get("listing") else [svc["url"]])
        if not urls:
            raise RuntimeError("no video link on the listing page")
        tried = 0
        while urls and tried < 4:
            url = urls.pop(0)
            tried += 1
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(6000)
            click_first(page, CONSENT)
            page.wait_for_timeout(2500)
            start_playback(page, svc)
            if not svc.get("listing"):
                break
            t_clip = time.time()
            good = long_enough(page)
            log("    clip", url.rsplit("/", 1)[-1][:50], "long enough" if good else "skipped", f"({int(time.time() - t_clip)} s)")
            if good:
                # all VPNs in this run watch the same clip: fair, and no new search for each VPN
                CLIP[svc["id"]] = url
                break
            if url == cached:  # today's clip stopped working: search the listing again
                CLIP.pop(svc["id"], None)
                cached = None
                urls = [u for u in listing_urls(page, svc) if u != url]
                tried = 0
        res["url"] = page.url
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
                for pat, why, kind in BLOCK_TEXTS:
                    if re.search(pat, body, re.I):
                        res.update(status="blocked", reason=why, kind=kind)
                        break
                if res["status"] == "blocked" and res["reason"] in RELOAD_ON and not res.get("reloaded") and start is None:
                    # A viewer reloads the page after a player error. The bot does the same, one time, and says so.
                    log("   ", res["reason"], "- reload the page one time")
                    res.update(status="none", reason=None, kind=None, reloaded=True)
                    page.reload(wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_timeout(6000)
                    click_first(page, CONSENT)
                    page.wait_for_timeout(2500)
                    start_playback(page, svc)
                    t0 = time.time()
                    continue
                if res["status"] == "blocked" and time.time() - t0 > 60:
                    break
        if start and last:
            played = round(last["t"] - start[1], 1)
            wall = time.time() - start[0]
            res.update(played_seconds=played, wait_seconds=ads_until, resolution=f'{last["w"]}x{last["h"]}', drm=last["drm"])
            if played >= CFG["watch_seconds"] - 8:
                res.update(status="ok", reason=None, kind=None)
            elif played >= 3:
                res.update(status="unstable", reason=f"Film grał {int(played)} s w ciągu {int(wall)} s", kind="stall")
            else:
                res.update(status="blocked", reason="Film nie ruszył", kind="timeout")
        elif res["status"] != "blocked":
            res.update(status="blocked", reason="Film nie ruszył w ciągu %d s" % CFG["max_wait_seconds"], kind="timeout")
        if res.get("kind") in NOT_VPN:
            res["status"] = "none"
        if not shot_done:
            save_shot(page, shot_path)
        res["shot"] = str(shot_path.relative_to(SITE))
    except Exception as e:  # a bot fault is "not tested", never "blocked"
        vpn = re.search(r"ERR_SOCKS|ERR_PROXY|ERR_TUNNEL|ERR_CONNECTION", str(e))
        res.update(status="none", reason=VPN_DOWN if vpn else "Błąd bota: " + type(e).__name__, kind="vpn_down" if vpn else "bot")
        log("  bot error:", type(e).__name__, str(e)[:160])
    finally:
        ctx.close()
    return res


VPN_DOWN = "Serwer VPN nie odpowiadał"
OUTAGE = "Serwis nie odpowiadał (awaria po stronie serwisu, nie VPN)"


def http_code(url, proxy):
    cmd = ["curl", "-s", "-o", "/dev/null", "-L", "--max-time", "25", "-w", "%{http_code}", "-A", "Mozilla/5.0"]
    if proxy:
        cmd += ["--socks5-hostname", f"127.0.0.1:{PORT}"]
    try:
        return int(subprocess.run(cmd + [url], capture_output=True, text=True).stdout or 0)
    except Exception:
        return 0


def service_down(svc):
    """True when the service itself fails: no answer or a 5xx error, through the VPN and directly."""
    url = svc.get("listing") or svc.get("url")
    codes = [http_code(url, True), http_code(url, False)]
    return all(c == 0 or c >= 500 for c in codes)


def jwt_groups(text):
    """Polsat Box Go: the access groups inside the session token (loc:pl, loc:world, vpn:true ...)."""
    import base64
    try:
        tok = json.loads(text)["result"]
        part = tok.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("accessGroups", [])
    except Exception:
        return None


def check_service(browser, svc, shot_path):
    """Access check without playback (no login, no paid plan): does the service treat the VPN address as Polish?
    status: ok | blocked | none. vpn_flag: True when the service marks the address as a VPN (Polsat Box Go only)."""
    res = {"status": "none", "reason": None, "kind": None, "tested_at": now().isoformat(timespec="seconds")}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
    page = ctx.new_page()
    seen = {}

    def on_resp(r):
        try:
            if svc["check"] == "wppilot" and "/api/v1/user/location" in r.url:
                seen["loc"] = r.json().get("data") or {}
            elif svc["check"] == "pbg" and "/rpc/system/" in r.url and "groups" not in seen:
                g = jwt_groups(r.text())
                if g:
                    seen["groups"] = g
        except Exception:
            pass
    page.on("response", on_resp)
    try:
        page.goto(svc["url"], wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(9000)
        click_first(page, CONSENT)
        page.wait_for_timeout(3000)
        body = ""
        try:
            body = page.evaluate("()=>document.body.innerText.slice(0,20000)")
        except Exception:
            pass
        if svc["check"] == "wppilot":
            loc = seen.get("loc")
            if re.search(r"nie możesz oglądać poza", body, re.I) or (loc and loc.get("iso_code") != "PL"):
                res.update(status="blocked", kind="geo", reason="Serwis pokazał komunikat: nie możesz oglądać poza Europejskim Obszarem Gospodarczym")
            elif loc and loc.get("iso_code") == "PL":
                res.update(status="ok")
            res["country"] = (loc or {}).get("iso_code")
        else:
            g = seen.get("groups")
            if g:
                res["country"] = "PL" if "loc:pl" in g else "inny"
                res["vpn_flag"] = "vpn:true" in g
                if "loc:pl" in g:
                    res.update(status="ok")
                else:
                    res.update(status="blocked", kind="geo", reason="Serwis nie uznał adresu za polski")
        if res["status"] == "none":
            res.update(reason="Serwis nie podał lokalizacji", kind="bot")
        save_shot(page, shot_path)
        res["shot"] = str(shot_path.relative_to(SITE))
    except Exception as e:
        vpn = re.search(r"ERR_SOCKS|ERR_PROXY|ERR_TUNNEL|ERR_CONNECTION", str(e))
        res.update(status="none", reason=VPN_DOWN if vpn else "Błąd bota: " + type(e).__name__, kind="vpn_down" if vpn else "bot")
        log("  check error:", type(e).__name__, str(e)[:160])
    finally:
        ctx.close()
    return res


def hist_status(entry, r):
    """Status for the history file. 'okr' = a paid plan played after one reload or in the second try (same rule as the site)."""
    s = r["status"]
    if s == "ok" and r.get("reloaded"):
        return "okr"
    if s == "unstable" and entry.get("plan") == "plan płatny" and (r.get("reason") or "").startswith("Pierwsza próba"):
        return "okr"
    return s


def tunnel_alive():
    """Is the tunnel up and is the exit address still Polish?"""
    for _ in range(2):
        try:
            if fetch_json("https://ipinfo.io/json", proxy=True, timeout=15).get("country") == "PL":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def ensure_tunnel(holder, conf):
    """Reconnect a dead tunnel (the browser keeps the same local proxy port). True when it is up."""
    if tunnel_alive():
        return True
    for n in range(2):
        log("   tunnel is down - reconnect", n + 1)
        holder[0].close()
        time.sleep(5)
        holder[0] = make_tunnel(conf)
        if tunnel_alive():
            return True
    return False


def main():
    day = now().strftime("%Y-%m-%d")
    started = now()
    runner = fetch_json("https://ipinfo.io/json")
    run = {"date": day, "started_at": started.isoformat(timespec="seconds"),
           "runner": {"country": runner.get("country")},  # country only: a local run must not publish the owner's city
           "watch_seconds": CFG["watch_seconds"], "providers": [], "services": [
               {"id": s["id"], "name": s["name"], "enabled": s.get("enabled", False)} for s in CFG["services"] if not s.get("check")],
           "checks": [{"id": s["id"], "name": s["name"]} for s in CFG["services"] if s.get("check") and s.get("enabled")]}
    services = [s for s in CFG["services"] if s.get("enabled") and not s.get("check")]
    checks = [s for s in CFG["services"] if s.get("enabled") and s.get("check")]
    with sync_playwright() as p:
        for prov in CFG["providers"]:
            entry = {"id": prov["id"], "name": prov["name"], "plan": prov.get("plan"), "server": prov.get("server"),
                     "tested": False, "services": {}, "checks": {}}
            run["providers"].append(entry)
            if not prov.get("enabled"):
                continue
            conf = pia_conf() if prov.get("pia") else secret_for(prov["secret_env"])
            if conf and prov.get("auth_env"):  # OpenVPN provider: config + login
                auth = secret_for(prov["auth_env"])
                conf = conf + "\x00" + auth if auth else None
            if not conf:
                entry["note"] = "Brak konfiguracji VPN"
                log(prov["name"], "- no secret, skipped")
                continue
            log(prov["name"], "- connecting")
            tun = [make_tunnel(conf)]
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
                        if not ensure_tunnel(tun, conf):
                            r = {"status": "none", "reason": VPN_DOWN, "kind": "vpn_down", "tested_at": now().isoformat(timespec="seconds")}
                        else:
                            r = test_service(browser, svc, shot)
                            if r["status"] != "ok":
                                # One failed try is not proof of a block. Check the VPN and try one more time.
                                log("   first try failed:", r.get("reason"), "- second try")
                                first, first_reason = r["status"], r.get("reason")
                                if ensure_tunnel(tun, conf):
                                    r = test_service(browser, svc, shot)
                                    r["attempts"] = 2
                                    if r["status"] == "ok" and first == "blocked":
                                        r.update(status="unstable", reason="Pierwsza próba nieudana (%s), druga udana" % first_reason)
                                    elif r["status"] == "blocked" and not tunnel_alive():
                                        # The film did not start because the VPN server dropped. That is not a block by the service.
                                        r.update(status="none", reason=VPN_DOWN, kind="vpn_down")
                                else:
                                    r = {"status": "none", "reason": VPN_DOWN, "kind": "vpn_down", "tested_at": now().isoformat(timespec="seconds"), "attempts": 1}
                        if r["status"] == "blocked" and r.get("kind") in ("timeout", "player") and service_down(svc):
                            r.update(status="none", reason=OUTAGE, kind="outage")
                        entry["services"][svc["id"]] = r
                        log("   ->", r["status"], r.get("reason") or "", r.get("played_seconds"))
                    for svc in checks:
                        log("  checking", svc["name"])
                        shot = DATA / "shots" / day / f'{prov["id"]}-{svc["id"]}.webp'
                        if not ensure_tunnel(tun, conf):
                            r = {"status": "none", "reason": VPN_DOWN, "kind": "vpn_down", "tested_at": now().isoformat(timespec="seconds")}
                        else:
                            r = check_service(browser, svc, shot)
                            if r["status"] != "ok" and ensure_tunnel(tun, conf):
                                r = check_service(browser, svc, shot)
                                r["attempts"] = 2
                        entry["checks"][svc["id"]] = r
                        log("   ->", r["status"], r.get("country"), "vpn flag" if r.get("vpn_flag") else "", r.get("reason") or "")
                finally:
                    browser.close()
                entry["tested"] = any(r["status"] != "none" for r in entry["services"].values())
            finally:
                tun[0].close()
    run["finished_at"] = now().isoformat(timespec="seconds")

    tested = [e for e in run["providers"] if e["tested"]]
    if not tested:
        log("No provider was tested. Nothing published.")
        return 1
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(run, ensure_ascii=False, indent=1))
    hist_f = DATA / "history.json"
    hist = json.loads(hist_f.read_text()) if hist_f.exists() else {"days": {}}
    # a second run on the same day updates the VPNs it tested and keeps the others' earlier results
    hist["days"][day] = {**hist["days"].get(day, {}), **{e["id"]: {k: hist_status(e, v) for k, v in e["services"].items()} for e in tested}}
    hist["days"] = dict(sorted(hist["days"].items())[-90:])
    # access checks (no playback) live apart from the playback history, so playback counts stay the same
    hist.setdefault("checks", {})[day] = {**hist["checks"].get(day, {}), **{e["id"]: {k: v["status"] for k, v in e.get("checks", {}).items()} for e in tested if e.get("checks")}}
    hist["checks"] = dict(sorted(hist["checks"].items())[-90:])
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
