# Polski Streaming Monitor

A bot tests each day which VPN can play Polish streaming services, and a static site shows the results.

- `bot/bot.py` runs the tests. `bot/config.json` lists the VPN providers and the services. To add one, edit the config and add a GitHub secret with its WireGuard config.
- `site/` is the website. The bot writes `site/data/latest.json`, `site/data/history.json` and screenshots in `site/data/shots/`.
- `.github/workflows/daily.yml` runs the bot each morning and commits the results. Vercel deploys the site after each commit.

Local run: put a WireGuard config in `bot/secrets/PROTON_PL_WG.conf`, then `xvfb-run -a python3 bot/bot.py`.
