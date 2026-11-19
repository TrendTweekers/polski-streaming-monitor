#!/usr/bin/env python3
"""One-time probe for new services (WP Pilot, Polsat Box Go). Opens the live pages, clicks the first
channel, and saves the visible text, screenshots and JSON responses to out/svc/<tag>/. Not published.
Usage: python bot/svc_probe.py <tag> [--vpn]"""
import json, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot
from playwright.sync_api import sync_playwright

TAG = sys.argv[1]
OUT = bot.ROOT.parent / "out" / "svc" / TAG
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [
    ("wp-tv", "https://pilot.wp.pl/tv/"),
    ("wp-tvp1", "https://pilot.wp.pl/tv/?channel=tvp-1-hd"),
    ("pbg-live", "https://polsatboxgo.pl/live"),
]


def main():
    tun = None
    if "--vpn" in sys.argv:
        tun = bot.Tunnel(bot.secret_for("NORD_PL_WG"))
    rep = {"country": bot.fetch_json("https://ipinfo.io/json", proxy=bool(tun)).get("country"), "pages": {}}
    with sync_playwright() as p:
        kw = dict(headless=False, executable_path=os.environ.get("BOT_CHROME") or None,
                  args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required", "--mute-audio"])
        if tun:
            kw["proxy"] = {"server": bot.PROXY}
        br = p.chromium.launch(**kw)
        for pid, url in PAGES:
            ctx = br.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
            page = ctx.new_page()
            net = []

            def on_resp(r, net=net):
                try:
                    if "json" in r.headers.get("content-type", "") or "/api/" in r.url or "rpc" in r.url:
                        net.append({"u": r.url[:250], "s": r.status, "b": r.text()[:2500]})
                except Exception:
                    pass
            page.on("response", on_resp)
            r = {}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(8000)
                bot.click_first(page, bot.CONSENT)
                page.wait_for_timeout(3000)
                page.screenshot(path=str(OUT / f"{pid}-1.png"))
                # click the first channel tile / play control
                for sel in ["[class*='channel'] a", "a[href*='channel']", "a[href*='/live/']", "[class*='play']", "[class*='Channel']"]:
                    try:
                        e = page.locator(sel).first
                        if e.is_visible():
                            r["clicked"] = sel
                            e.click(timeout=4000)
                            break
                    except Exception:
                        pass
                page.wait_for_timeout(12000)
                try:  # Polsat Box Go: a free highlight clip
                    e = page.get_by_text("Zobacz skrót").first
                    if e.is_visible():
                        e.click(timeout=4000)
                        r["clicked2"] = "Zobacz skrót"
                except Exception:
                    pass
                page.wait_for_timeout(20000)
                page.screenshot(path=str(OUT / f"{pid}-2.png"))
                r["final"] = page.url
                r["videos"] = bot.videos(page)
                r["text"] = page.evaluate("()=>document.body.innerText")[:4000]
            except Exception as e:
                r["err"] = str(e)[:300]
            r["net"] = net[:120]
            rep["pages"][pid] = r
            ctx.close()
            print(pid, r.get("final"), r.get("err"), flush=True)
        br.close()
    if tun:
        tun.close()
    (OUT / "rep.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
