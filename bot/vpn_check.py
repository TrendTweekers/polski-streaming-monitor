#!/usr/bin/env python3
"""Check that a provider's tunnel gives a Polish exit address. Usage: vpn_check.py <provider id>. Prints no secrets."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot

pid = sys.argv[1]
prov = next(p for p in bot.CFG["providers"] if p["id"] == pid)
conf = bot.pia_conf() if prov.get("pia") else bot.secret_for(prov["secret_env"])
if conf and prov.get("auth_env"):
    auth = bot.secret_for(prov["auth_env"])
    conf = conf + "\x00" + auth if auth else None
if not conf:
    sys.exit(f"{pid}: no secret")
t = bot.make_tunnel(conf)
try:
    ip = bot.fetch_json("https://ipinfo.io/json", proxy=True)
    print(pid, "exit:", ip.get("country"), ip.get("city"), ip.get("org"))
    print(pid, "speed Mb/s:", bot.speed_mbps())
    sys.exit(0 if ip.get("country") == "PL" else 1)
finally:
    t.close()
