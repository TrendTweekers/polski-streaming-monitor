#!/usr/bin/env python3
"""Send the daily test result (or a failure note) to the owner in Telegram. Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."""
import json, os, sys, urllib.request, pathlib

LABEL = {"ok": "działa", "unstable": "niestabilny", "blocked": "NIE DZIAŁA", "none": "nie przetestowano"}


def send(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("no Telegram settings, message not sent"); return
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, headers={"Content-Type": "application/json"})
    print(urllib.request.urlopen(req, timeout=20).status)


def main():
    if len(sys.argv) > 1:  # free text, e.g. a failure note from the workflow
        return send(" ".join(sys.argv[1:]))
    run = json.loads((pathlib.Path(__file__).resolve().parent.parent / "site/data/latest.json").read_text())
    names = {s["id"]: s["name"] for s in run["services"]}
    lines = [f'Polski Streaming, test {run["date"]}']
    for p in run["providers"]:
        if not p.get("tested"):
            continue
        ok = sum(1 for r in p["services"].values() if r["status"] == "ok")
        lines.append(f'\n{p["name"]} ({p.get("plan") or "-"}): {ok} z {len(p["services"])} działa, {p.get("speed_mbps", "?")} Mb/s')
        for sid, r in p["services"].items():
            why = f' ({r["reason"]})' if r.get("reason") and r["status"] != "ok" else ""
            lines.append(f'  {names.get(sid, sid)}: {LABEL.get(r["status"], r["status"])}{why}')
    lines.append("\nhttps://polskistreaming.pl/wyniki-testow")
    send("\n".join(lines))


if __name__ == "__main__":
    main()
