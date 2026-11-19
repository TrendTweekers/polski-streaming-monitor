#!/usr/bin/env python3
"""One-time probe of the TVP live channels (vod.tvp.pl/live): first WITHOUT a VPN from the runner's own
country, then through the NordVPN server in Poland. Saves screenshots, visible text and video state to
out/live/ (not published). Run by .github/workflows/live.yml."""
import json, os, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot
from playwright.sync_api import sync_playwright

OUT = bot.ROOT.parent / "out" / "live"
OUT.mkdir(parents=True, exist_ok=True)
LIVE = [("tvp1", "TVP 1", "https://vod.tvp.pl/live,1/tvp-1,399697"), ("tvp2", "TVP 2", "https://vod.tvp.pl/live,1/tvp-2,399698"),
        ("tvpinfo", "TVP Info", "https://vod.tvp.pl/live,1/tvp-info,399699")]
MSG = re.compile(r"[^\n]*(zablokowan|licencyjn|niedostępn|poza granicami|terytorium|adblock|wystąpił problem|coś poszło nie tak|vpn)[^\n]*", re.I)


def texts(page):
    out = []
    for f in page.frames:
        try:
            out.append(f.evaluate("()=>document.body?document.body.innerText:''"))
        except Exception:
            pass
    return "\n".join(out)


def probe(p, name, proxy):
    res = {}
    br = p.chromium.launch(headless=False, proxy={"server": bot.PROXY} if proxy else None, executable_path=os.environ.get("BOT_CHROME") or None,
                           args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required", "--mute-audio"])
    for cid, cname, url in LIVE:
        ctx = br.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
        page = ctx.new_page(); r = {"url": url}
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(7000)
            bot.click_first(page, bot.CONSENT)
            page.wait_for_timeout(3000)
            r["program"] = page.evaluate("()=>{const h=document.querySelector('h1');return h?h.innerText.trim().slice(0,160):''}")
            # The red "Na żywo" button under the programme title (not the menu link with the same text).
            r["clicked"] = page.evaluate("""()=>{const e=[...document.querySelectorAll('a,button')].filter(x=>/^na żywo$/i.test((x.innerText||'').trim())&&x.getBoundingClientRect().top>300)[0];if(e){e.click();return true}return false}""")
            page.wait_for_timeout(40000)
            page.screenshot(path=str(OUT / f"{name}-{cid}-40s.png"))
            page.wait_for_timeout(140000)  # adverts before the live picture can take about 3 minutes
            if proxy:  # through the VPN the advert block was longer: look again after 5 and 7 minutes
                page.screenshot(path=str(OUT / f"{name}-{cid}-3min.png"))
                page.wait_for_timeout(120000)
                page.screenshot(path=str(OUT / f"{name}-{cid}-5min.png"))
                page.wait_for_timeout(120000)
            a = bot.videos(page)
            page.wait_for_timeout(15000)
            b = bot.videos(page)
            r["final_url"] = page.url
            r["title"] = page.title()
            r["videos_a"], r["videos_b"] = a, b
            r["played"] = any(y["w"] > 0 and y["t"] - x["t"] > 8 for x, y in zip(a, b)) if a and b else False
            t = texts(page)
            r["messages"] = sorted(set(m.group(0).strip() for m in MSG.finditer(t) if len(m.group(0)) < 260))[:25]
            r["text"] = t[:5000]
            page.screenshot(path=str(OUT / f"{name}-{cid}.png"))
        except Exception as e:
            r["error"] = type(e).__name__ + ": " + str(e)[:200]
        finally:
            ctx.close()
        res[cid] = r
        print(name, cid, "played" if r.get("played") else "NOT played", r.get("messages"), r.get("error"), flush=True)
    br.close()
    return res


def main():
    report = {"when": bot.now().isoformat(timespec="seconds"), "runner_country": bot.fetch_json("https://ipinfo.io/json").get("country"), "passes": {}}
    with sync_playwright() as p:
        if "--vpn-only" not in sys.argv:
            report["passes"]["novpn"] = probe(p, "novpn", False)
        conf = bot.secret_for("NORD_PL_WG")
        if conf and "--novpn-only" not in sys.argv:
            tun = bot.Tunnel(conf)
            try:
                ip = bot.fetch_json("https://ipinfo.io/json", proxy=True)
                report["vpn_exit"] = {"country": ip.get("country"), "city": ip.get("city"), "org": ip.get("org")}
                if ip.get("country") == "PL":
                    report["passes"]["nord"] = probe(p, "nord", True)
            finally:
                tun.close()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
