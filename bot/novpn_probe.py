#!/usr/bin/env python3
"""One-time probe: open the test videos WITHOUT a VPN (from the runner's own country) and save
what the services show: a screenshot and the visible text. Output goes to out/novpn/ (not published)."""
import json, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot
from playwright.sync_api import sync_playwright

OUT = bot.ROOT.parent / "out" / "novpn" if (bot.ROOT.name == "bot") else bot.ROOT / "out" / "novpn"
OUT.mkdir(parents=True, exist_ok=True)
EXTRA = [{"id": "polsat", "name": "Polsat Box Go", "url": "https://polsatboxgo.pl/", "play": "oglądaj"}]


def main():
    report = {"ip": bot.fetch_json("https://ipinfo.io/json").get("country"), "services": {}}
    with sync_playwright() as p:
        br = p.chromium.launch(headless=False, executable_path=os.environ.get("BOT_CHROME") or None,
                               args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required", "--mute-audio"])
        for svc in [s for s in bot.CFG["services"] if s.get("enabled")] + EXTRA:
            ctx = br.new_context(viewport={"width": 1440, "height": 900}, locale="pl-PL", timezone_id="Europe/Warsaw")
            page = ctx.new_page(); r = {}
            try:
                urls = bot.listing_urls(page, svc) if svc.get("listing") else [svc["url"]]
                r["url"] = urls[0] if urls else None
                if urls:
                    page.goto(urls[0], wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_timeout(6000)
                    bot.click_first(page, bot.CONSENT)
                    page.wait_for_timeout(2000)
                    page.screenshot(path=str(OUT / f'{svc["id"]}-1-page.png'))
                    try:
                        bot.start_playback(page, svc)
                    except Exception as e:
                        r["play_error"] = type(e).__name__
                    page.wait_for_timeout(45000)
                    r["final_url"] = page.url
                    r["videos"] = bot.videos(page)
                    texts = []
                    for f in page.frames:
                        try:
                            texts.append(f.evaluate("()=>document.body?document.body.innerText:''"))
                        except Exception:
                            pass
                    r["text"] = "\n".join(texts)[:6000]
                    page.screenshot(path=str(OUT / f'{svc["id"]}-2-after.png'))
            except Exception as e:
                r["error"] = type(e).__name__ + ": " + str(e)[:200]
            finally:
                ctx.close()
            report["services"][svc["id"]] = r
            print(svc["id"], r.get("final_url"), r.get("error"), flush=True)
        br.close()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
