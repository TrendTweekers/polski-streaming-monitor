#!/usr/bin/env python3
"""Send the daily test result (or a failure note) to the owner in Telegram. Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."""
import json, os, sys, urllib.request, pathlib

ICON = {"ok": "✅", "unstable": "⚠️", "blocked": "❌", "none": "➖"}
WHY = [("Film nie ruszył w ciągu", "the film did not start in time"), ("Film nie ruszył", "the film did not start"),
       ("Pierwsza próba nieudana", "first try failed, second try OK"), ("Serwer VPN nie odpowiadał", "the VPN server did not answer"),
       ("blokowaniu reklam", "the service showed an ad-block message"), ("blokadzie regionalnej", "the service showed a region block"),
       ("wykrył VPN", "the service detected the VPN"), ("błąd odtwarzania", "the service showed a player error"),
       ("Film grał", "the film stopped early"), ("Błąd bota", "bot error")]
PLAN = {"plan płatny": "paid", "plan darmowy": "free"}


def why_en(reason):
    for pl, en in WHY:
        if pl in (reason or ""):
            return en
    return reason or ""


def send(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("no Telegram settings, message not sent"); return
    body = json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, headers={"Content-Type": "application/json"})
    print(urllib.request.urlopen(req, timeout=20).status)


def main():
    if len(sys.argv) > 1:  # free text, e.g. a failure note from the workflow
        return send(" ".join(sys.argv[1:]))
    run = json.loads((pathlib.Path(__file__).resolve().parent.parent / "site/data/latest.json").read_text())
    names = {s["id"]: s["name"] for s in run["services"]}
    lines = [f'📺 <b>Polski Streaming · daily test {run["date"]}</b>']
    for p in run["providers"]:
        if not p.get("tested"):
            continue
        rs = p["services"]
        ok = sum(1 for r in rs.values() if r["status"] == "ok")
        lines.append(f'\n<b>{p["name"]}</b> ({PLAN.get(p.get("plan"), p.get("plan") or "-")}) · {ok}/{len(rs)} work · {p.get("speed_mbps", "?")} Mb/s')
        for sid, r in rs.items():
            why = f' <i>({why_en(r.get("reason"))})</i>' if r["status"] != "ok" and r.get("reason") else ""
            if r["status"] == "ok" and r.get("reloaded"):
                why = " <i>(after one page reload)</i>"
            lines.append(f'{ICON.get(r["status"], "?")} {names.get(sid, sid)}{why}')
    lines.append("\nhttps://polskistreaming.pl/wyniki-testow")
    send("\n".join(lines))


if __name__ == "__main__":
    main()
