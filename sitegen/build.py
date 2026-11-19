"""Build the static site: python3 sitegen/build.py

Writes site/*.html, site/style.css and site/app.js. Test data (site/data/) is written
by the bot and is not touched here.

Content rules:
- No invented test results. A provider or service that the bot did not test says so.
- Provider facts come from the provider's own pages; each has a source and a check date.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent / "site"
DOMAIN = "https://polskistreaming.pl"
UPDATED = "10 listopada 2026"
CHECKED = "16.11.2026"
PRICED = "19.11.2026"  # prices and Black Friday offers read from the provider pages (out/bf.py)
PUBLISHED = "2026-11-10"
MODIFIED = "2026-11-10"
INDEXABLE = True  # set True when the owner opens the site to search engines
# Pages kept out of search until they have enough substance of their own.
NOINDEX = {"/polsat-box-go-za-granica", "/wyniki-testow", "/prywatnosc"}
_latest = SITE / "data" / "latest.json"
RUN = json.loads(_latest.read_text()) if _latest.exists() else {"providers": [], "services": []}
SVON = [x for x in RUN.get("services", []) if x.get("enabled")]
ST_LABEL = {"okr": 'Działa<small class="stn">po odświeżeniu</small>', "ok": "Działa", "blocked": "Nie działa", "unstable": "Niestabilny", "none": "Nie przetestowano"}
ST_ICON = {"okr": '<path d="M20 6 9 17l-5-5"/>', "ok": '<path d="M20 6 9 17l-5-5"/>', "blocked": '<path d="M18 6 6 18M6 6l12 12"/>',
           "unstable": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>', "none": '<path d="M5 12h14"/>'}


def shown(p, r):
    """Display status. A paid VPN that played after one reload counts as working, with a note."""
    s = r.get("status", "none")
    if s == "ok" and r.get("reloaded"):
        return "okr"
    if s == "unstable" and p.get("plan") == "plan płatny" and (r.get("reason") or "").startswith("Pierwsza próba"):
        return "okr"
    return s


def st(status):
    return (f'<span class="st {"ok" if status == "okr" else status}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ST_ICON[status]}</svg>{ST_LABEL[status]}</span>')


def fmt_dt(iso):
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}, {iso[11:16]}" if iso else "—"


def tested():
    return [p for p in RUN.get("providers", []) if p.get("tested")]


def tested_companies():
    """Distinct VPN companies in the last run (Proton paid and Proton free are one company)."""
    out = []
    for p in tested():
        if p["name"] not in out:
            out.append(p["name"])
    return out


TEST_SINCE = {"nord": "11.11.2026", "proton": "13.11.2026", "protonfree": "10.11.2026"}
TEST_NAME = {"nord": "NordVPN", "proton": "Proton VPN Plus", "protonfree": "darmowy serwer Proton VPN"}
_hist = SITE / "data" / "history.json"
HIST = json.loads(_hist.read_text()) if _hist.exists() else {"days": {}}


def tested_since_line():
    """Who is tested since when, and who is not tested. For the ranking."""
    done = [f'{TEST_NAME[p["id"]]} od {TEST_SINCE[p["id"]]}' for p in tested() if p["id"] in TEST_SINCE]
    names = set(tested_companies())
    todo = [n for n in ("NordVPN", "Surfshark", "Proton VPN", "ExpressVPN", "CyberGhost") if n not in names]
    return ("<b>Testujemy codziennie:</b> " + ", ".join(done) + "."
            + (" <b>Jeszcze nie testujemy:</b> " + ", ".join(todo) + ". Ich miejsce wynika tylko z danych ze stron dostawców." if todo else ""))


def svc_days(sid, note, n=10):
    """Day-by-day results of one service, newest first."""
    days = sorted(HIST.get("days", {}), reverse=True)[:n]
    cols = [pid for pid in ("nord", "proton", "protonfree") if any(pid in HIST["days"][d] for d in days)]
    short = {"nord": "NordVPN", "proton": "Proton Plus", "protonfree": "Proton, darmowy"}
    head = "".join(f"<th>{short[c]}</th>" for c in cols)
    rows = ""
    for d in days:
        cells = ""
        for c in cols:
            v = HIST["days"][d].get(c, {}).get(sid)
            cells += f"<td>{st(v)}</td>" if v else '<td class="muted">—</td>'
        rows += f"<tr><th>{d[8:10]}.{d[5:7]}</th>{cells}</tr>"
    return (f'<div class="scrollx keep"><table class="mini3 days"><thead><tr><th>2026</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="muted small">{note}</p>')


def tested_cta(service, lead):
    """Buttons only for the VPNs we really test every day, with the partner note."""
    rows = ""
    for pid, name, since, srv in (("nord", "NordVPN", "11.11.2026", "Warszawa"), ("proton", "Proton VPN", "13.11.2026", "PL#213, Warszawa")):
        pr = PROFILE[pid]
        url = next(f[2] for f in FACTS if f[0] == pid)
        rows += (f'<div class="prow"><img src="{LOGOS[pid]}" alt="" width="34" height="34"><b>{name}</b>'
                 f'<span><em>W teście z {service}</em>codziennie od {since}</span><span><em>Cena</em>{pr["price"]} {pr["unit"]}</span><span><em>Serwer w teście</em>{srv}</span>'
                 f'<span class="pcta"><a class="btn" {plink(pid, url)}>Zobacz ofertę {name}</a>{aff_note(pid)}</span></div>')
    return f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>VPN, które testujemy z {service}</h2><p>{lead}</p></div>
  <p class="disc">Przyciski to linki partnerskie: przy zakupie dostajemy prowizję, a Ty płacisz tyle samo. Nie wpływa to na wynik testu.</p>
  <div class="pstrip">{rows}</div>
</div></section>"""


def tested_phrase():
    """'NordVPN (plan płatny) i Proton VPN (plan darmowy)', built from the last bot run."""
    names = [p["name"] + (f' ({p["plan"]})' if p.get("plan") else "") for p in tested()]
    return (", ".join(names[:-1]) + " i " + names[-1]) if len(names) > 1 else (names[0] if names else "żaden dostawca")


def nord_test_line():
    if not any(p["id"] == "nord" for p in tested()):
        return ""
    return f'<p class="feattest">Nasz test z {LAST[:10]}: {prov_status_html("nord")}</p>'


def prov_status_html(pid):
    """Static copy of what app.js renders, so the result is in the HTML that search engines read."""
    p = next((x for x in RUN.get("providers", []) if x["id"] == pid), None)
    if not p or not p.get("tested"):
        return st("none")
    return "".join(f'<span class="pst">{x["name"]}:{st(shown(p, p["services"].get(x["id"], {})))}</span>' for x in SVON)


def svc_rows_html(sid):
    out = ""
    for p in tested():
        r = p["services"].get(sid)
        if not r:
            continue
        plan = f' ({p["plan"]})' if p.get("plan") else ""
        why = f'. {r["reason"]}' if r.get("reason") and shown(p, r) != "okr" else ""
        link = f'<a href="/{r["shot"]}" target="_blank" rel="noopener">zrzut ekranu</a>' if r.get("shot") else "<span></span>"
        out += (f'<div class="svcrow"><img src="{LOGOS[p["id"]]}" alt="" width="30" height="30"><b>{p["name"]}{plan}</b>{st(shown(p, r))}'
                f'<span class="muted">Test: {fmt_dt(r.get("tested_at"))}{why}</span>{link}</div>')
    return out or '<p class="muted" style="padding:14px 0">Tego serwisu jeszcze nie testujemy.</p>'


def last_rows_html(plan=None):
    out = ""
    for p in tested():
        if plan and p.get("plan") != plan:
            continue
        plan = f' ({p["plan"]})' if p.get("plan") else ""
        out += (f'<div class="lastrow"><img src="{LOGOS[p["id"]]}" alt="" width="30" height="30"><b>{p["name"]}{plan}</b><span>{prov_status_html(p["id"])}</span>'
                f'<span class="muted">Test: {fmt_dt(RUN.get("finished_at"))}</span></div>')
    return out or '<p class="muted">Brak wyniku testu.</p>'

NAV = [("/tvp-vod-za-granica", "TVP VOD"), ("/player-za-granica", "Player"), ("/tvp-sport-za-granica", "TVP Sport"), ("/darmowy-vpn-polska-telewizja", "Darmowy VPN"),
       ("/porownanie-vpn", "Ranking VPN"), ("/wyniki-testow", "Wyniki testów"), ("/jak-testujemy", "Jak testujemy")]


def layout(path, title, desc, body, kind="page", crumbs=None):
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == path else "", t) for h, t in NAV)
    index = INDEXABLE and path not in NOINDEX
    robots = "" if index else '<meta name="robots" content="noindex, follow">\n'
    url = DOMAIN + ("" if path == "/" else path)
    org = {"@type": "Organization", "@id": DOMAIN + "/#org", "name": "Polski Streaming", "url": DOMAIN, "logo": DOMAIN + "/apple-touch-icon.png"}
    graph = [org]
    if path == "/":
        graph.append({"@type": "WebSite", "@id": DOMAIN + "/#site", "url": DOMAIN, "name": "Polski Streaming", "inLanguage": "pl", "publisher": {"@id": DOMAIN + "/#org"}})
    if kind == "article":
        graph.append({"@type": "Article", "headline": title.split(" | ")[0], "description": desc, "inLanguage": "pl", "mainEntityOfPage": url,
                      "datePublished": PUBLISHED, "dateModified": MODIFIED, "image": DOMAIN + "/og.jpg",
                      "author": {"@id": DOMAIN + "/#org"}, "publisher": {"@id": DOMAIN + "/#org"}})
    if crumbs:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + ("" if h == "/" else h)} for i, (h, n) in enumerate(crumbs)]})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="impact-site-verification" value="7e5c2fe8-11cc-46c9-a6db-9950f62d1bfb">
{robots}<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#17232D">
<meta property="og:type" content="{'article' if kind == 'article' else 'website'}">
<meta property="og:site_name" content="Polski Streaming">
<meta property="og:locale" content="pl_PL">
<meta property="og:title" content="{title.split(' | ')[0]}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMAIN}/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="/fonts/ibm-plex-sans-400-latin-ext.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/manrope-var-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css">
<script>document.documentElement.className="js"</script>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="/"><i aria-hidden="true"></i>Polski Streaming</a>
  <nav class="cnav" aria-label="Główne">{nav}</nav>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">
  <div><b>Polski Streaming</b><br>Niezależne testy VPN z polskimi serwisami streamingowymi.</div>
  <nav><a href="/polsat-box-go-za-granica">Polsat Box Go</a><a href="/wyniki-testow">Wyniki testów</a><a href="/o-nas">O nas</a><a href="mailto:kontakt@polskistreaming.pl">kontakt@polskistreaming.pl</a><a href="/jak-testujemy">Jak testujemy</a><a href="/jak-testujemy#linki">Linki partnerskie</a><a href="/prywatnosc">Prywatność</a></nav>
</div></footer>
<script src="/app.js" defer></script>
<script>window.va=window.va||function(){{(window.vaq=window.vaq||[]).push(arguments)}};</script>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def band(crumb, h1, lead, extra="", image=False, figure=""):
    if image is True:
        img = ('<img class="hero" src="/hero-uk.webp" srcset="/hero-uk-sm.webp 887w, /hero-uk.webp 1774w" sizes="(max-width:820px) 100vw, 780px" '
               'width="1774" height="887" alt="Ilustracja: połączenie z zagranicy do Polski">')
    elif image:
        img = f'<img class="hero art" src="/img/{image}.webp" alt="" width="1022" height="311">'
    else:
        img = ""
    credit = '<div class="credit">Ilustracja. To nie jest zrzut ekranu z testu.</div>' if image else ""
    if figure:
        img = figure
    return f"""<div class="open{'' if (image or figure) else ' solo'}{' hasfig' if figure else ''}"><div class="wrap">
  <div class="otext">
    <div class="crumb">{crumb}</div>
    <h1>{h1}</h1>
    <p>{lead}</p>
    {extra}
  </div>
  {img}
</div>{credit}</div>"""


LAST = fmt_dt(RUN.get("finished_at"))

WHEN = f"""<div class="when mono">
      <span>Ostatni test: <b id="last">{LAST}</b></span>
      <span>Kolejny: <b id="next">—</b></span>
    </div>"""

RESULTS = """<section class="results" id="wyniki"><div class="wrap">
  <div class="rhead">
    <div><h2>Wyniki ostatniego testu</h2><p id="scope">Kliknij nazwę VPN, aby zobaczyć szczegóły testu.</p></div>
    <div class="nums">
      <div><b id="s1">—</b><span>testowanych VPN-ów działa z TVP VOD</span></div>
      <div><b id="s2">—</b><span>prób w ostatnim teście</span></div>
      <div><b id="s3">—</b><span>dni testów w historii</span></div>
    </div>
  </div>
  <div class="sortbar" role="group" aria-label="Sortowanie">Sortuj według:
    <button type="button" data-sort="works" aria-pressed="true">działających serwisów</button>
    <button type="button" data-sort="speed" aria-pressed="false">prędkości</button>
  </div>
  <div class="desk"><table><thead><tr id="thead"></tr></thead><tbody id="rows"></tbody></table></div>
  <div class="mlist" id="mlist"></div>
  <div class="rfoot">
    <div class="legend" id="legend"></div>
    <div><a href="/jak-testujemy">Jak testujemy</a></div>
  </div>
</div></section>
<section class="feat"><div class="wrap">
  <div class="freecta">
    <div><h2>Darmowy serwer bywa przeciążony. Płatne VPN mają ich więcej.</h2>
      <p>W planie darmowym wielu ludzi korzysta z tych samych serwerów w Polsce. Gdy serwer jest przeciążony albo serwis zablokuje jego adres, trudno przełączyć się na inny. NordVPN podaje 61 serwerów w Polsce i daje 30 dni na zwrot pieniędzy.</p></div>
    <a class="btn big" href="/porownanie-vpn">Zobacz ranking VPN</a>
  </div>
</div></section>"""

HISTORY = """<section class="history" id="historia"><div class="wrap">
  <div class="shead"><h2>Skuteczność w ostatnich 30 dniach</h2><p>VPN, który działa dziś, jutro może przestać działać. Złe dni zostają w historii. Szare pola to dni bez testu.</p></div>
  <div class="hctl">
    <div class="seg" role="group" aria-label="VPN" id="hprov"></div>
    <div class="seg" role="group" aria-label="Serwis" id="hserv"></div>
  </div>
  <div class="hgrid">
    <div class="chartbox"><div id="chart"></div></div>
    <div class="hsum">
      <div><b id="h1">—</b><span>udanych testów</span></div>
      <div><b id="h2">—</b><span>dni, w których nie działał</span></div>
      <div><b id="h3">—</b><span>dni testów w ostatnich 30 dniach</span></div>
    </div>
  </div>
  <div class="matrix">
    <div id="matrix"></div>
    <div class="maxis" aria-hidden="true"><span></span><div><span id="ax0"></span><span id="ax1"></span><span id="ax2"></span></div><span></span></div>
  </div>
</div></section>"""

EVIDENCE = """<section class="evidence" id="dowod"><div class="wrap">
  <div class="shead"><h2>Dowód z ostatniego testu</h2><p>Bot robi zrzut ekranu przy każdej próbie, także nieudanej. Kliknij zrzut, aby otworzyć go w pełnym rozmiarze.</p></div>
  <div class="egrid">
    <div><div id="shot"></div><div class="thumbs" id="thumbs"></div></div>
    <dl>
      <dt>Serwis</dt><dd id="e0">—</dd>
      <dt>VPN</dt><dd id="e1">—</dd>
      <dt>Serwer VPN</dt><dd id="e2b" class="mono">—</dd>
      <dt>Adres IP serwera</dt><dd id="e2">—</dd>
      <dt>Data</dt><dd id="e4" class="mono">—</dd>
      <dt>Godzina</dt><dd id="e5" class="mono">—</dd>
      <dt>Wynik</dt><dd id="e3"></dd>
      <dt>Pomiar</dt><dd id="e6">—</dd>
      <dt>Kryterium</dt><dd>60 s filmu bez przerwy</dd>
    </dl>
  </div>
</div></section>"""


def svc_result(sid, name, note):
    return f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Wynik naszego testu: {name}</h2><p>{note}</p></div>
  <div class="svc" data-svc="{sid}">{svc_rows_html(sid)}</div>
  <p class="after"><a href="/wyniki-testow#historia">Historia 30 dni</a> · <a href="/wyniki-testow#dowod">Wszystkie zrzuty ekranu</a> · <a href="/jak-testujemy">Jak testujemy</a></p>
</div></section>"""


def steps(title, lead, items):
    lis = "".join(f'<li><span class="n">{i + 1:02d}</span><h3>{h}</h3><p>{t}</p></li>' for i, (h, t) in enumerate(items))
    return f"""<section class="howto"><div class="wrap">
  <div class="side"><h2>{title}</h2><p>{lead}</p></div>
  <ol class="hsteps">{lis}</ol>
</div></section>"""


def facts_box(title, rows, note=""):
    trs = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f'<h2>{title}</h2><table class="mini"><tbody>{trs}</tbody></table>' + (f'<p class="muted small">{note}</p>' if note else "")


def errors_box(rows, title="Komunikaty błędów i co z nimi zrobić"):
    trs = "".join(f"<tr><td>„{m}”</td><td>{w}</td><td>{d}</td></tr>" for m, w, d in rows)
    return (f'<h2>{title}</h2><div class="scrollx keep"><table class="mini3"><thead><tr><th>Komunikat</th><th>Co oznacza</th><th>Co zrobić</th></tr></thead>'
            f"<tbody>{trs}</tbody></table></div>")


BYLINE = '<span>Autor: <a href="/o-nas">Redakcja Polski Streaming</a></span>'


def frame(src, url, cap):
    """A real bot screenshot inside a plain browser frame."""
    return (f'<figure class="bframe"><div class="bbar"><i></i><i></i><i></i><span>{url}</span></div>'
            f'<img src="{src}" alt="{cap}" width="1440" height="900"><figcaption>{cap}</figcaption></figure>')


def flow(service, logo=""):
    flags = "".join(f'<img src="/flags/{c}.svg" alt="" width="30" height="20">' for c in ("gb", "de", "nl", "us"))
    tv = ('<svg class="tvico" viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
          '<rect x="2.5" y="4.5" width="19" height="12.5" rx="1.6"/><path d="M8 20.5h8M12 17v3.5"/><path d="M10.2 8.6v4.3l3.8-2.15z" fill="currentColor" stroke="none"/></svg>')
    end = f'<span class="slogo"><img src="{logo}" alt=""></span>' if logo else tv
    return f"""<div class="flow" role="img" aria-label="Ty za granicą, serwer VPN w Polsce, {service}">
  <div class="fnode"><div class="fico">{flags}</div><b>Ty, za granicą</b><span>Zagraniczny adres IP</span></div>
  <div class="fline"><span>szyfrowane połączenie</span></div>
  <div class="fnode mid"><div class="fico"><img src="/flags/pl.svg" alt="" width="42" height="28"></div><b>Serwer VPN w Polsce</b><span>Polski adres IP</span></div>
  <div class="fline"><span>polski adres IP</span></div>
  <div class="fnode"><div class="fico">{end}</div><b>{service}</b><span>Widzi widza z Polski</span></div>
</div>"""


FLOWS = {}


def provstrip(note=""):
    rows = ""
    for pid, name, url, pl, refund, dev, tv, src, srcname, n in FACTS:
        pr = PROFILE[pid]
        rows += (f'<div class="prow"><img src="{LOGOS[pid]}" alt="" width="34" height="34"><b>{RANK[pid]}. {name}</b>'
                 f'<span><em>Cena</em>{pr["price"]} {pr["unit"]}</span>'
                 f'<span><em>Nasz test {LAST[:10]}</em>{test_summary(pid)}</span><span><em>Serwer w Polsce</em>{pl}</span>'
                 f'<span class="pcta"><a class="btn" {plink(pid, url)}>Zobacz ofertę {name}</a>{aff_note(pid)}</span></div>')
    return f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>VPN z serwerem w Polsce</h2><p>{note or 'Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.'}</p></div>
  {DISCLOSE}
  <div class="pstrip">{rows}</div>
  <p class="after"><a href="/porownanie-vpn">Pełne porównanie i źródła danych</a></p>
</div></section>"""


def prose(html, cls="faqs", aside=""):
    for k, v in FLOWS.items():
        html = html.replace(f"<!--flow:{k}-->", v)
    side = f'<aside class="side2">{aside}</aside>' if aside else ""
    return f'<section class="{cls}"><div class="wrap pgrid"><div class="prose">{html}</div>{side}</div></section>'


def brief(rows, links=()):
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    ln = "".join(f'<a href="{h}">{t}</a>' for h, t in links)
    return f'<div class="brief"><h3>W skrócie</h3><dl>{dl}</dl><div class="blinks">{ln}</div></div>'


def shot(sid, name):
    return f'<figure class="sidefig" data-shot="{sid}"></figure><p class="figcap">Zrzut ekranu z ostatniego testu: {name}.</p>'


def faq(items):
    rows = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in items)
    return f'<section class="faqs" id="faq"><div class="wrap"><div class="shead"><h2>Częste pytania</h2></div><div class="faq">{rows}</div></div></section>'


LEGAL_Q = ("Czy to jest legalne?", "Używanie VPN jest legalne w Wielkiej Brytanii, Unii Europejskiej i USA. Regulamin serwisu streamingowego może jednak zabraniać omijania blokad regionalnych. Przeczytaj regulamin swojego serwisu.")
FREE_Q = ("Czy darmowy VPN wystarczy?", "Czasem tak. Obok płatnych planów NordVPN i Proton VPN Plus testujemy codziennie darmowy serwer Proton VPN w Polsce. Jego wynik zmienia się z dnia na dzień. Aktualny wynik jest na górze tej strony. Darmowe serwery są obciążone, więc film może się zacinać.")
TV_Q = ("Czy to działa na telewizorze?", "Tak, jeśli Twój telewizor albo przystawka ma aplikację VPN. Większość dostawców ma aplikacje na Android TV, Fire TV i Apple TV. Szczegóły są w <a href=\"/porownanie-vpn\">porównaniu VPN</a>.")

FACTS = [
    ("nord", "NordVPN", "https://nordvpn.com", "Tak, 61 serwerów (Warszawa)", "30 dni", "10", "Windows, macOS, Linux, Android, iOS, Android TV, Apple TV, Fire TV",
     "https://nordvpn.com/servers/poland/", "nordvpn.com/servers/poland", ""),
    ("surf", "Surfshark", "https://surfshark.com", "Tak, Warszawa", "30 dni", "Bez limitu", "Windows, macOS, Linux, Android, iOS, Android TV, Apple TV, Fire TV",
     "https://surfshark.com/pricing", "surfshark.com/pricing", ""),
    ("proton", "Proton VPN", "https://protonvpn.com", "Tak", "30 dni", "10", "Windows, macOS, Linux, Android, iOS, Android TV, Apple TV, Fire TV",
     "https://protonvpn.com/pricing", "protonvpn.com/pricing", ""),
    ("cybr", "CyberGhost", "https://www.cyberghostvpn.com", "Tak, 1 lokalizacja", "45 dni (14 dni w planie miesięcznym)", "7", "Windows, macOS, Linux, Android, iOS, Android TV, Apple TV, Fire TV",
     "https://www.cyberghostvpn.com/vpn-server", "cyberghostvpn.com/vpn-server", ""),
    ("expr", "ExpressVPN", "https://www.expressvpn.com", "Tak, Warszawa", "30 dni (dla nowych klientów)", "Do 14", "Windows, macOS, Linux, Android, iOS, Android TV, Apple TV, Fire TV",
     "https://www.expressvpn.com/vpn-server/poland-vpn", "expressvpn.com/vpn-server/poland-vpn", ""),
]

# Ranking: points for published facts only (no test results, no commission). Columns:
# serwery w Polsce, cena, urządzenia, zwrot, aplikacje TV, płatność w zł
REFUND = {f[0]: re.match(r"\d+ dni", f[4]).group(0) for f in FACTS}
POINTS = {"surf": (1, 3, 3, 2, 3, 1), "nord": (3, 2, 2, 2, 3, 1), "proton": (1, 3, 2, 2, 3, 1), "cybr": (1, 3, 1, 3, 3, 0), "expr": (1, 2, 3, 2, 3, 0)}  # 19.11.2026: Black Friday prices moved both one price step up
WEIGHTS = (2, 1, 1, 1, 1, 1)  # servers in Poland count double: the most important fact for Polish TV
MAXPTS = 19


def wpts(pid):
    return [x * w for x, w in zip(POINTS[pid], WEIGHTS)]


RANK = {pid: i + 1 for i, pid in enumerate(["nord", "surf", "proton", "cybr", "expr"])}
assert sorted(RANK, key=lambda p: -sum(wpts(p)))[:3] == ["nord", "surf", "proton"]
EUR = "4,3895 zł (kurs średni NBP z 10.11.2026)"


def points_table():
    names = {f[0]: f[1] for f in FACTS}
    rows = "".join(f'<tr><td><b>{RANK[pid]}. {names[pid]}</b></td>' + "".join(f"<td>{x}</td>" for x in wpts(pid)) + f'<td><b>{sum(wpts(pid))}</b></td></tr>' for pid in RANK)
    return ('<div class="scrollx keep"><table class="mini3 pts"><thead><tr><th>Dostawca</th><th>Serwery w Polsce (×2)</th><th>Cena</th><th>Urządzenia</th><th>Zwrot</th><th>Aplikacje TV</th><th>Płatność w zł</th><th>Razem</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


# Partner (affiliate) links. A provider without an entry gets a plain link to its home page.
AFF = {
    "nord": "https://www.jdoqocy.com/click-101925411-13382109",  # CJ link suggested by the NordVPN manager 2026-11-11 (lands on /special/, Polish page for visitors from Poland). Before: 15078184
    "surf": "https://www.dpbolvw.net/click-101925411-15438560",  # CJ advertiser 6282055, text link "Get Surfshark VPN right away" (home page)
    "proton": "https://www.dpbolvw.net/click-101925411-15834536",  # CJ advertiser 5227916, text link "Proton VPN - Special Offer" (Polish offer page)
    "expr": "https://go.expressvpn.com/c/8234307/1636009/16063",  # Impact, link from Ana 2026-11-19, lands on the Polish page (program 16063); page tag goes in subId1
}
AFF_NAMES = {"surf": "Surfshark", "nord": "NordVPN", "proton": "Proton VPN", "cybr": "CyberGhost", "expr": "ExpressVPN"}


def partners():
    """Polish list of today's partners, e.g. 'NordVPN, Surfshark i Proton VPN'."""
    n = [AFF_NAMES[k] for k in AFF_NAMES if k in AFF]
    return n[0] if len(n) == 1 else ", ".join(n[:-1]) + " i " + n[-1]


PARTNERS = None  # set after AFF is complete


def plink(pid, url):
    """href + rel for a button to a provider. Partner links are marked rel=sponsored."""
    if pid in AFF:
        return f'href="{AFF[pid]}" target="_blank" rel="sponsored nofollow noopener" data-aff="{pid}"'
    return f'href="{url}" target="_blank" rel="nofollow noopener"'


def aff_note(pid):
    """Small line under a button: refund time, and the partner label when the link is a partner link."""
    refund = REFUND.get(pid, "")
    bits = ([f"{refund} na zwrot pieniędzy"] if refund else []) + (["Link partnerski"] if pid in AFF else [])
    return f'<small class="affn">{" · ".join(bits)}</small>' if bits else ""


SVC_INS = {"tvpvod": "TVP VOD", "player": "Playerem", "tvpsport": "TVP Sport"}  # after "z": z Playerem


def join_pl(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " i " + xs[-1]


def _works(p, sid):
    return shown(p, p["services"].get(sid, {})) in ("ok", "okr")


def pick(sid=None):
    """The first paid partner VPN (ranking order) that played in the last bot run.
    With sid: it must work with that service. Without: with every tested service, else the one with most."""
    paid = sorted((p for p in tested() if p.get("plan") == "plan płatny" and p["id"] in AFF), key=lambda p: RANK.get(p["id"], 99))
    sids = [sid] if sid else [x["id"] for x in SVON]
    best = (None, [])
    for p in paid:
        ok = [x for x in sids if _works(p, x)]
        if len(ok) == len(sids):
            return p, ok
        if len(ok) > len(best[1]):
            best = (p, ok)
    return best


def test_summary(pid):
    p = next((x for x in tested() if x["id"] == pid), None)
    if not p:
        return "Jeszcze nie testujemy"
    n = sum(1 for x in SVON if _works(p, x["id"]))
    return f"Działa: {n} z {len(SVON)} serwisów"


def today_box(sid=None, kicker=""):
    """Result of the last real test plus one button. Built from the bot data, so it never claims more than the test showed."""
    p, ok = pick(sid)
    if not p:
        what = SVC_INS[sid] if sid else "polskimi serwisami"
        return (f'<div class="today none"><p><b>W ostatnim teście ({LAST[:10]}) żaden płatny VPN nie zagrał z {what}.</b> '
                f'Tak bywa: wynik zmienia się z dnia na dzień. <a href="/wyniki-testow#historia">Zobacz wyniki dzień po dniu</a>.</p></div>')
    pid, name, pr = p["id"], p["name"], PROFILE[p["id"]]
    url = next(f[2] for f in FACTS if f[0] == pid)
    r = p["services"][ok[0]]
    when = fmt_dt(r.get("tested_at")) if sid else LAST[:10]
    shot = f' · <a href="/{r["shot"]}" target="_blank" rel="noopener">zrzut ekranu</a>' if sid and r.get("shot") else ' · <a href="/wyniki-testow">wyniki</a>'
    k = f'<p class="todayk">{kicker}</p>' if kicker else ""
    return (f'<div class="today">{k}<div class="todayh"><img src="{LOGOS[pid]}" alt="" width="34" height="34">'
            f'<p><b>{name} działa z {join_pl([SVC_INS[x] for x in ok])}</b><span>Nasz test: {when}, serwer w Polsce{shot}</span></p></div>'
            f'<div class="todayc"><a class="btn big" {plink(pid, url)}>Zobacz ofertę {name}</a>'
            f'<small>{pr["price"]} {pr["unit"]} · {REFUND[pid]} na zwrot pieniędzy · Link partnerski</small></div></div>')


def sticky_bar(sid=None):
    """Small bar at the bottom of the phone screen, shown after some scrolling. Same data as today_box."""
    p, ok = pick(sid)
    if not p:
        return ""
    pid, name = p["id"], p["name"]
    url = next(f[2] for f in FACTS if f[0] == pid)
    what = SVC_INS[sid] if sid else "polską telewizją"
    return (f'<div class="sbar" id="sbar"><img src="{LOGOS[pid]}" alt="" width="30" height="30"><span><b>{name} działa z {what}</b><small>Nasz test: {LAST[:10]} · Link partnerski</small></span>'
            f'<a class="btn" {plink(pid, url)}>Zobacz ofertę</a><button type="button" aria-label="Zamknij">×</button></div>')


TODAY = {"/tvp-vod-za-granica": "tvpvod", "/player-za-granica": "player", "/tvp-sport-za-granica": "tvpsport",
         "/tvp-vod-material-niedostepny-w-twoim-kraju": "tvpvod", "/player-niedostepny-w-twojej-lokalizacji": "player", "/tvp-sport-material-niedostepny": "tvpsport",
         "/polska-telewizja-w-uk": None, "/polska-telewizja-w-niemczech": None, "/darmowy-vpn-polska-telewizja": None}


def with_today(path, body):
    """Put the tested-VPN box right under the short answer, and add the phone bar."""
    if path not in TODAY:
        return body
    sid = TODAY[path]
    kick = "Gdy darmowy serwer nie zagra, płatny plan z naszego testu:" if path.startswith("/darmowy") else ""
    i = body.find('<p class="answer">')
    assert i >= 0, path
    j = body.find("</p>", i) + 4
    return body[:j] + today_box(sid, kick) + body[j:] + sticky_bar(sid)


DISCLOSE = ('<p class="disc">Przyciski __PARTNERS__ to linki partnerskie. Gdy kupisz przez nie VPN, dostajemy prowizję, '
            'a Ty płacisz tyle samo. Prowizja nie daje punktów w rankingu i nie zmienia wyników testu.</p>')


PROFILE = {
    "proton": dict(tag="Najniższa cena w zestawieniu", badge="", price="6,29 zł", unit="za miesiąc",
                   terms="Plan na 2 lata w ofercie Black Friday (−75%), płatny z góry: 6,29 zł × 24 miesiące. Cena z oferty dla partnerów, sprawdzona 16.11.2026. Bez promocji 24,99 zł za miesiąc.",
                   pros=["Najniższa cena w zestawieniu", "10 urządzeń jednocześnie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                   cons=["Najniższa cena tylko w planie na 2 lata, odnowienie jest droższe"]),
    "nord": dict(tag="Najwięcej serwerów w Polsce", badge="", price="9,39 zł", unit="za miesiąc",
                 terms="253,53 zł za pierwsze 27 miesięcy.",
                 pros=["61 serwerów w Polsce, najwięcej w zestawieniu", "10 urządzeń jednocześnie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Najniższa cena tylko w planie na 27 miesięcy"]),
    "surf": dict(tag="Bez limitu urządzeń", badge="", price="8,99 zł", unit="za miesiąc",
                 terms="242,73 zł za pierwsze 27 miesięcy, plus VAT, jeśli dotyczy.",
                 pros=["Bez limitu urządzeń", "8,99 zł za miesiąc w planie na 27 miesięcy", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Do ceny może dojść VAT"]),
    "expr": dict(tag="Najwięcej urządzeń z limitem: 14", badge="", price="ok. 10,49 zł", unit="za miesiąc (2,39 €)",
                 terms="66,92 € za pierwsze 28 miesięcy, potem 79,95 € za rok. Cena z oferty Black Friday, sprawdzona 19.11.2026. Przeliczenie na złote po kursie NBP z 10.11.2026 (4,3895 zł). Bank może policzyć inaczej.",
                 pros=["Do 14 urządzeń jednocześnie", "Serwer w Warszawie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Cena tylko w euro", "Zwrot w 30 dni tylko dla nowych klientów"]),
    "cybr": dict(tag="Najdłuższy zwrot pieniędzy: 45 dni", badge="", price="ok. 8,74 zł", unit="za miesiąc (1,99 €)",
                 terms="55,72 € za pierwsze 28 miesięcy. Cena z oferty Black Friday, sprawdzona 19.11.2026. Plan na 1 miesiąc: 11,99 €. Przeliczenie na złote po kursie NBP z 10.11.2026 (4,3895 zł). Bank może policzyć inaczej.",
                 pros=["45 dni na zwrot (14 dni w planie miesięcznym)", "7 urządzeń jednocześnie", "Jest plan na jeden miesiąc"],
                 cons=["Jedna lokalizacja w Polsce", "Cena tylko w euro"]),
}
PRICE_SRC = {"proton": ("https://protonvpn.com/pl/l/bf-vpn-offers-2026", "protonvpn.com, oferta Black Friday"), "nord": ("https://nordvpn.com/pl/pricing/", "nordvpn.com/pl/pricing"),
             "surf": ("https://surfshark.com/pl/pricing", "surfshark.com/pl/pricing"), "expr": ("https://www.expressvpn.com/pl/pricing", "expressvpn.com/pl/pricing"),
             "cybr": ("https://www.cyberghostvpn.com/pl/buy/cyberghost-vpn-3", "cyberghostvpn.com")}
CHECK = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>'
MINUS = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>'


BF_ON = True  # switch off when the Black Friday offers end
BF = {  # as shown on each provider's Polish pricing page on PRICED: (discount, paid up front, price without the offer, after the first period)
    "nord": ("−75% i 3 miesiące ekstra", "253,53 zł za pierwsze 27 miesięcy", "37,59 zł za miesiąc", "Dostawca podaje cenę odnowienia przy zamówieniu"),
    "surf": ("−90% i 3 miesiące ekstra", "242,73 zł za pierwsze 27 miesięcy, plus VAT", "33,18 zł za miesiąc", "Dostawca podaje cenę odnowienia przy zamówieniu"),
    "proton": ("−75% w planie na 2 lata", "150,96 zł za pierwsze 24 miesiące", "24,99 zł za miesiąc", "209,88 zł co 12 miesięcy"),
    "cybr": ("−83%, 2 lata i 4 miesiące", "55,72 € za pierwsze 28 miesięcy", "11,99 € za miesiąc (plan miesięczny)", "55,72 € za rok"),
    "expr": ("−81%, 2 lata i 4 miesiące", "66,92 € za pierwsze 28 miesięcy", "12,99 € za miesiąc", "79,95 € za rok"),
}


def bf_box():
    if not BF_ON:
        return ""
    rows = ""
    for pid in sorted(RANK, key=RANK.get):
        name, pr = AFF_NAMES[pid], PROFILE[pid]
        url = next(f[2] for f in FACTS if f[0] == pid)
        rows += (f'<div class="prow"><img src="{LOGOS[pid]}" alt="" width="34" height="34"><b>{name}</b>'
                 f'<span><em>Rabat według dostawcy</em>{BF[pid][0]}</span><span><em>Cena</em>{pr["price"]} {pr["unit"]}</span>'
                 f'<span><em>Płacisz z góry</em>{BF[pid][1]}</span>'
                 f'<span class="pcta"><a class="btn" {plink(pid, url)}>Zobacz ofertę {name}</a>{aff_note(pid)}</span></div>')
    return f"""<section class="results bf" id="black-friday"><div class="wrap narrowpad">
  <div class="shead"><h2>Black Friday 2026: oferty VPN z serwerem w Polsce</h2><p>Ceny i rabaty odczytaliśmy ze stron dostawców {PRICED}. Dostawcy nie podają daty końca promocji, więc oferta może się zmienić z dnia na dzień. Kolejność jak w rankingu.</p></div>
  <div class="pstrip">{rows}</div>
  <p class="after">Rabat liczy dostawca, zwykle od ceny planu miesięcznego. Po pierwszym okresie plan odnawia się drożej. <a href="/promocje-vpn">Ceny bez promocji i ceny odnowienia</a></p>
</div></section>"""


def bf_bar():
    if not BF_ON:
        return ""
    top = " · ".join(f"{AFF_NAMES[pid]} {BF[pid][0].split(' ')[0].rstrip(',')}" for pid in sorted(RANK, key=RANK.get)[:3])
    return (f'<section class="bfbar"><div class="wrap"><b>Black Friday 2026</b><span>{top}. Ceny z {PRICED}.</span>'
            f'<a href="/promocje-vpn">Zobacz wszystkie oferty</a></div></section>')


TOP3_WHY = {
    "nord": "61 polskich serwerów, najwięcej w zestawieniu",
    "surf": "Jeden plan na dowolną liczbę urządzeń",
    "proton": "Najniższa cena przy planie na 2 lata",
}


def score10(pid):
    """Ranking points on a 10 scale (16 of 19 points = 8,4). The same public points, only easier to read."""
    return f"{sum(wpts(pid)) / MAXPTS * 10:.1f}".replace(".", ",")


def day_bars(pid, n=14):
    """One small bar per test day, oldest first: green = every tested service played, red = none, amber = some."""
    days = sorted(HIST.get("days", {}))[-n:]
    cells, good, done = "", 0, 0
    for d in days:
        v = list(HIST["days"][d].get(pid, {}).values())
        if not v:
            c, t = "none", "bez testu"
        else:
            ok = sum(1 for x in v if x in ("ok", "okr"))
            done += 1
            if ok == len(v):
                c, t = "ok", "działa"; good += 1
            elif ok == 0:
                c, t = "blocked", "nie działa"
            else:
                c, t = "unstable", f"działa {ok} z {len(v)}"
        cells += f'<i class="{c}" title="{d[8:10]}.{d[5:7]}: {t}"></i>'
    if not done:
        return ""
    return (f'<span class="dbars" role="img" aria-label="Dni testów: {done}, w pełni udane: {good}">{cells}</span>'
            f'<small class="dbl">{good} z {done} dni testów bez błędu</small>')


def rank_rows(n=5):
    """Compact ranking rows: place, score, proof from our test, price, button."""
    daily = {p["id"] for p in tested() if p.get("plan") == "plan płatny"}
    out = ""
    for pid in sorted(RANK, key=RANK.get)[:n]:
        name, pr = AFF_NAMES[pid], PROFILE[pid]
        url = next(f[2] for f in FACTS if f[0] == pid)
        pros = "".join(f"<li>{CHECK}<span>{x}</span></li>" for x in pr["pros"][:3])
        if pid in daily:
            p = next(x for x in tested() if x["id"] == pid)
            nok = sum(1 for x in SVON if _works(p, x["id"]))
            cls = "ok" if nok == len(SVON) else ("blocked" if nok == 0 else "unstable")
            test = f'<b class="rrt {cls}">Test {LAST[:5]}: działa {nok} z {len(SVON)}</b>{day_bars(pid)}'
        else:
            test = '<b class="rrt none">Jeszcze nie testujemy</b><small class="dbl">Miejsce wynika z danych ze strony dostawcy</small>'
        deal = f'<em>{BF[pid][0]}</em>' if BF_ON else ""
        first = RANK[pid] == 1
        out += f"""<article class="rr{' first' if first else ''}">{'<span class="rrib">Nr 1 w rankingu</span>' if first else ''}
  <span class="rrn" aria-label="Miejsce {RANK[pid]}">#{RANK[pid]}</span>
  <div class="rrb"><img src="{LOGOS[pid]}" alt="" width="44" height="44"><div><b>{name}</b><span class="rrtag">{pr["tag"]}</span></div></div>
  <div class="rrs"><b>{score10(pid)}</b><span>/10</span><small>{sum(wpts(pid))} z {MAXPTS} pkt</small></div>
  <ul class="rrp">{pros}</ul>
  <div class="rrtest">{test}</div>
  <div class="rrpr"><b>{pr["price"]}</b><span>{pr["unit"]}</span>{deal}</div>
  <div class="pcta"><a class="btn big" {plink(pid, url)}>Zobacz ofertę</a>{aff_note(pid)}<a class="rrmore" href="/porownanie-vpn#{pid}">Szczegóły</a></div>
</article>"""
    return f'<div class="rrs5">{out}</div>'


SCORE_NOTE = (f'<p class="after">Ocena to punkty z naszego rankingu przeliczone na skalę 10, na przykład 16 z {MAXPTS} punktów daje 8,4. '
              'Punkty są za fakty ze stron dostawców, nie za prowizję. <a href="/porownanie-vpn#ranking">Zasady punktacji</a></p>')


def top3():
    """Short top 3 for the home page. The full ranking lives on /porownanie-vpn."""
    return f"""<section class="results soft"><div class="wrap narrowpad">
  <div class="shead"><h2>Top 3 VPN do polskiej telewizji</h2><p>Trzy pierwsze miejsca z naszego rankingu pięciu dostawców. Ceny z {PRICED}.</p></div>
  <p class="disc">Przyciski prowadzą przez linki partnerskie. Za zakup dostajemy prowizję, Twoja cena jest ta sama, a kolejność od niej nie zależy.</p>
  {rank_rows(3)}
  {SCORE_NOTE}
  <p class="after"><a href="/porownanie-vpn">Pełny ranking 5 VPN z cenami, wadami i zasadami punktów</a></p>
</div></section>"""


def rank_top():
    """Top of the ranking page: all five rows, then the labelled brand highlight."""
    return f"""<section class="results soft"><div class="wrap narrowpad">
  <div class="shead"><h2>Ranking w skrócie</h2><p>Kolejność wynika z punktów za fakty ze stron dostawców. Obok oceny pokazujemy wynik naszego codziennego testu, jeśli dany VPN już testujemy.</p></div>
  <p class="note">{tested_since_line()}</p>
  {DISCLOSE}
  {rank_rows(5)}
  {SCORE_NOTE}
  {brand_slot()}
</div></section>"""


def brand_slot():
    """A highlight that is clearly not a ranking place. ExpressVPN: best-known premium brand, place 5 by points."""
    pid = "expr"
    if pid not in AFF:
        return ""
    pr = PROFILE[pid]
    url = next(f[2] for f in FACTS if f[0] == pid)
    deal = f" W ofercie Black Friday: {BF[pid][0]}, {BF[pid][1]}." if BF_ON else ""
    return f"""<aside class="brand">
  <div><span class="brandk">Wyróżnienie redakcji · to nie jest miejsce w rankingu</span>
    <h3><img src="{LOGOS[pid]}" alt="" width="34" height="34">Znana marka premium: ExpressVPN</h3>
    <p>ExpressVPN to jedna z najbardziej znanych marek VPN na świecie. Ma serwer w Warszawie, aplikacje na Android TV, Apple TV i Fire TV oraz do 14 urządzeń w najwyższym planie.{deal} W naszym rankingu punktowym ma miejsce {RANK[pid]}, bo płaci się w euro i ma mniej serwerów w Polsce niż NordVPN. Jeszcze go nie testujemy z polskimi serwisami.</p></div>
  <div class="pcta"><b>{pr["price"]}</b><span>{pr["unit"]}</span><a class="btn big" {plink(pid, url)}>Zobacz ofertę ExpressVPN</a>{aff_note(pid)}</div>
</aside>"""


def home_hero():
    chips = "".join(f'<a href="{h}">{t}</a>' for h, t in (
        ("/tvp-vod-za-granica", '<img src="/logos/tvpvod.png" alt="" height="18">TVP VOD'), ("/player-za-granica", '<img src="/logos/player.svg" alt="" height="16">Player'),
        ("/tvp-sport-za-granica", "TVP Sport"), ("/polsat-box-go-za-granica", '<img src="/logos/polsat.svg" alt="" height="18">Polsat Box Go'),
        ("/darmowy-vpn-polska-telewizja", "Darmowy VPN")))
    ps = [p for p in tested() if p.get("plan") == "plan płatny"]
    return f"""<div class="open hh"><div class="wrap">
  <div class="otext">
    <div class="hhk">{CHECK}Ostatni test: {LAST}</div>
    <h1>Polska telewizja za granicą: jak oglądać i który VPN wybrać</h1>
    <p>Poradniki dla Polaków w Wielkiej Brytanii, Niemczech, Holandii i USA. Do tego codzienny test: sprawdzamy, czy film naprawdę gra przez VPN.</p>
    <ul class="hhl">
      <li>{CHECK}Test co rano: TVP VOD, Player i TVP Sport</li>
      <li>{CHECK}Zrzut ekranu z każdej próby</li>
      <li>{CHECK}Ranking według jawnych punktów</li>
    </ul>
    <div class="cta2"><a class="btn big" href="/porownanie-vpn">Zobacz ranking VPN</a><a class="btn big ghost" href="#status">Wynik dzisiejszego testu</a></div>
  </div>
  <img class="hero" src="/hero-uk.webp" srcset="/hero-uk-sm.webp 887w, /hero-uk.webp 1774w" sizes="(max-width:820px) 100vw, 620px" width="1774" height="887" alt="Ilustracja: połączenie z zagranicy do Polski">
</div><div class="credit">Ilustracja. To nie jest zrzut ekranu z testu.</div></div>
<div class="pickw"><div class="wrap"><div class="pick"><b>Co chcesz oglądać?</b><div>{chips}</div></div></div></div>"""


def how_home():
    """Home: how it works as three steps plus a real before/after from our own tests."""
    ic = lambda d: f'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{d}</svg>'
    steps = [
        (ic('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'), "Jesteś za granicą",
         "Polski serwis sprawdza Twój adres IP. Widzi adres z Wielkiej Brytanii, Niemiec albo USA i blokuje film."),
        (ic('<path d="M12 3 4 6v6c0 4.5 3.2 7.8 8 9 4.8-1.2 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>'), "Łączysz się z serwerem VPN w Polsce",
         "Aplikacja VPN szyfruje połączenie i wysyła je przez serwer w Warszawie. Dostajesz polski adres IP."),
        (ic('<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/><path d="m10 8 5 2.5-5 2.5z"/>'), "Serwis widzi widza z Polski",
         "Odświeżasz stronę i włączasz film. To, czy naprawdę ruszy, zależy od VPN i od dnia, dlatego testujemy to co rano."),
    ]
    lis = "".join(f'<li><span class="hwn">{i + 1}</span><span class="hwi">{svg}</span><div><h3>{h}</h3><p>{t}</p></div></li>' for i, (svg, h, t) in enumerate(steps))
    return f"""<section class="hw"><div class="wrap">
  <div class="shead"><h2>Jak to działa</h2><p>Polskie serwisy sprawdzają adres IP. VPN z serwerem w Polsce daje Ci polski adres, więc serwis traktuje Cię jak widza w kraju.</p></div>
  <div class="hwg">
    <ol class="hws">{lis}</ol>
    <div class="hwba">
      <figure class="hwf bad"><span class="hwtag">Bez VPN</span><img src="/img/blok-tvpvod.webp" alt="TVP VOD bez VPN: komunikat, że materiał jest niedostępny w Twoim kraju" width="1200" height="750" loading="lazy">
        <figcaption>TVP VOD z adresu w USA: materiał zablokowany. Nasz zrzut ekranu z 11.11.2026.</figcaption></figure>
      <span class="hwarrow" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
      <figure class="hwf good"><span class="hwtag">Z VPN w Polsce</span><img src="/img/tvpvod-test.webp" alt="TVP VOD przez VPN z serwerem w Polsce: program gra" width="1440" height="900" loading="lazy">
        <figcaption>Ten sam serwis przez serwer VPN w Polsce: „Jeden z dziesięciu” gra. Nasz test z 10.11.2026.</figcaption></figure>
    </div>
  </div>
  <p class="after"><a href="/jak-testujemy">Jak dokładnie testujemy</a> · <a href="/wyniki-testow">Wyniki dzień po dniu</a></p>
</div></section>"""


def guides_grid():
    groups = [
        ("Serwisy", [("/tvp-vod-za-granica", "Jak oglądać TVP VOD za granicą", "Trzy sposoby, wynik codziennego testu i to, na co uważać przy reklamach."),
                     ("/player-za-granica", "Jak oglądać Player za granicą", "Darmowe odcinki, pakiet Player International i test z VPN."),
                     ("/tvp-sport-za-granica", "Jak oglądać TVP Sport za granicą", "Materiały wideo a transmisje na żywo, wynik testu i liczby z pomiarów."),
                     ("/polsat-box-go-za-granica", "Jak oglądać Polsat Box Go za granicą", "Co działa w Unii Europejskiej i pakiet dla widzów za granicą.")]),
        ("Komunikaty błędów", [("/tvp-vod-material-niedostepny-w-twoim-kraju", "TVP VOD: „materiał jest niedostępny w Twoim kraju”", "Jak wygląda komunikat, skąd się bierze i trzy wyjścia."),
                               ("/player-niedostepny-w-twojej-lokalizacji", "„Player jest niedostępny w Twojej lokalizacji”", "Blokada całego serwisu poza Unią i co da się zrobić."),
                               ("/tvp-sport-material-niedostepny", "TVP Sport: „materiał jest niedostępny”", "Trzy wersje komunikatu i próba przed meczem.")]),
        ("Kraje i VPN", [("/polska-telewizja-w-niemczech", "Polska telewizja w Niemczech", "Satelita, pakiety Vodafone i Telekom z cenami, polskie serwisy i VPN."),
                         ("/polska-telewizja-w-uk", "Polska telewizja w UK", "Co działa po brexicie: satelita, Player International, TV Licence i VPN."),
                         ("/darmowy-vpn-polska-telewizja", "Darmowy VPN do polskiej telewizji", "Jak ustawić darmowy serwer w Polsce i co pokazał nasz test."),
                         ("/promocje-vpn", "Promocje VPN: Black Friday 2026", "Ceny z promocji, ceny bez promocji i ile płacisz z góry.")]),
    ]
    ico = {"Serwisy": '<path d="M8 5v14l11-7z"/>', "Komunikaty błędów": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
           "Kraje i VPN": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'}
    cols = "".join(f'<div class="ggc g{n}"><h3><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ico[g]}</svg>{g}</h3>' + "".join(f'<a href="{h}"><b>{t}</b><span>{d}</span></a>' for h, t, d in items) + "</div>" for n, (g, items) in enumerate(groups))
    return f"""<section class="guides"><div class="wrap">
  <div class="shead"><h2>Poradniki</h2><p>Wybierz serwis, komunikat albo kraj. Każdy poradnik pokazuje legalne opcje bez VPN i sposób z VPN.</p></div>
  <div class="gg">{cols}</div>
</div></section>"""


def pill(status):
    """Status as a filled pill for the dark status board."""
    cls = "ok" if status in ("ok", "okr") else status
    note = '<small>po odświeżeniu</small>' if status == "okr" else ""
    label = {"ok": "Działa", "okr": "Działa", "blocked": "Nie działa", "unstable": "Niestabilny", "none": "Bez testu"}[status]
    return (f'<span class="pill {cls}"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ST_ICON[status]}</svg>{label}</span>{note}')


def status_matrix():
    """Home page: the last test as a dark status board (static copy of the bot data)."""
    order = {"nord": 0, "proton": 1, "protonfree": 2}
    names = {"nord": "NordVPN", "proton": "Proton VPN Plus", "protonfree": "Proton VPN, darmowy"}
    plans = {"nord": "plan płatny", "proton": "plan płatny", "protonfree": "plan darmowy"}
    slogo = {"tvpvod": '<img src="/logos/tvpvod.png" alt="" height="16">', "player": '<img src="/logos/player.svg" alt="" height="14">'}
    ps = sorted(tested(), key=lambda x: order.get(x["id"], 9))
    if not ps:
        return ""
    head = "".join(f'<span class="smh">{slogo.get(x["id"], "")}{x["name"]}</span>' for x in SVON)
    rows, tries, good = "", 0, 0
    for p in ps:
        pid = p["id"]
        cells = ""
        for x in SVON:
            stt = shown(p, p["services"].get(x["id"], {}))
            tries += stt != "none"
            good += stt in ("ok", "okr")
            cells += f'<span class="smc"><em>{x["name"]}</em>{pill(stt)}</span>'
        aid = "proton" if pid == "protonfree" else pid
        url = next(f[2] for f in FACTS if f[0] == aid)
        cta = (f'<a class="btn" {plink(aid, url)}>Zobacz ofertę</a>{aff_note(aid)}' if p.get("plan") == "plan płatny"
               else '<a class="smfree" href="/darmowy-vpn-polska-telewizja">Jak ustawić darmowy serwer</a>')
        rows += (f'<div class="smrow"><div class="smn"><img src="{LOGOS[pid]}" alt="" width="36" height="36"><div><b>{names.get(pid, p["name"])}</b><small>{plans.get(pid, "")}</small></div></div>'
                 f'{cells}<div class="smb">{day_bars(pid)}</div><div class="pcta">{cta}</div></div>')
    return f"""<section class="sm" id="status"><div class="wrap">
  <div class="smtop">
    <div><span class="smlive"><i></i>Test automatyczny · codziennie rano</span>
      <h2>Wynik testu z {LAST[:10]}</h2>
      <p>Bot łączy się przez serwer VPN w Polsce, włącza film i sprawdza, czy gra 60 sekund. Zapisuje zrzut ekranu z każdej próby.</p></div>
    <div class="smnums">
      <div><b>{good}/{tries}</b><span>prób udanych w ostatnim teście</span></div>
      <div><b>{len(SVON)}</b><span>serwisy: {", ".join(x["name"] for x in SVON)}</span></div>
      <div><b>{len(HIST.get("days", {}))}</b><span>dni testów w historii</span></div>
    </div>
  </div>
  <div class="smx"><div class="smrow smhead"><span>VPN w teście</span>{head}<span>Ostatnie dni</span><span></span></div>{rows}</div>
  <p class="smafter">Ostatni test: {LAST}. <a href="/wyniki-testow">Wszystkie wyniki, historia i zrzuty ekranu</a> · <a href="/jak-testujemy">Jak testujemy</a></p>
</div></section>"""


def deals_page():
    trs = ""
    for pid in sorted(RANK, key=RANK.get):
        name, pr = AFF_NAMES[pid], PROFILE[pid]
        url = next(f[2] for f in FACTS if f[0] == pid)
        ps, pn = PRICE_SRC[pid]
        trs += f"""<article class="deal" id="{pid}">
  <header><img src="{LOGOS[pid]}" alt="" width="44" height="44"><div><h3>{name}</h3><span class="rrtag">{BF[pid][0]}</span></div>
    <div class="rrpr"><b>{pr["price"]}</b><span>{pr["unit"]}</span></div></header>
  <dl>
    <dt>Cena bez promocji (według dostawcy)</dt><dd>{BF[pid][2]}</dd>
    <dt>Płacisz z góry</dt><dd>{BF[pid][1]}</dd>
    <dt>Po pierwszym okresie</dt><dd>{BF[pid][3]}</dd>
    <dt>Zwrot pieniędzy</dt><dd>{next(f[4] for f in FACTS if f[0] == pid)}</dd>
    <dt>Nasz test z polskimi serwisami ({LAST[:10]})</dt><dd>{test_summary(pid)}</dd>
    <dt>Źródło ceny</dt><dd><a href="{ps}" target="_blank" rel="nofollow noopener">{pn}</a>, odczyt {PRICED}</dd>
  </dl>
  <div class="pcta"><a class="btn big" {plink(pid, url)}>Zobacz ofertę {name}</a>{aff_note(pid)}</div>
</article>"""
    return trs


def featured():
    return f"""<section class="feat"><div class="wrap">
  <div class="featbox">
    <div class="feath"><span class="feattag">Nasz wybór do polskiej telewizji</span>
      <h2><img src="/logos/nord.svg" alt="" width="40" height="40">NordVPN</h2>
      <p>Ma 61 serwerów w Polsce, najwięcej w rankingu. Gdy serwis zablokuje jeden adres, przełączasz się na inny serwer i oglądasz dalej.</p>{nord_test_line()}</div>
    <ul class="featl">
      <li>{CHECK}<span>61 serwerów w Polsce</span></li>
      <li>{CHECK}<span>10 urządzeń jednocześnie</span></li>
      <li>{CHECK}<span>Aplikacje na Android TV, Apple TV i Fire TV</span></li>
      <li>{CHECK}<span>30 dni na zwrot pieniędzy</span></li>
    </ul>
    <div class="featcta"><b>9,39 zł</b><span>za miesiąc</span>
      <a class="btn big" {plink("nord", "https://nordvpn.com")}>Zobacz ofertę NordVPN</a>{aff_note("nord")}
      <small>253,53 zł za pierwsze 27 miesięcy. Cena z {PRICED}.</small></div>
  </div>
</div></section>"""


def highlights():
    items = [("nord", "Najwięcej serwerów w Polsce", "61 serwerów"), ("surf", "Bez limitu urządzeń", "8,99 zł za miesiąc"),
             ("cybr", "Najdłuższy zwrot pieniędzy", "45 dni"), ("expr", "Najwięcej urządzeń z limitem", "do 14 naraz"),
             ("proton", "Najniższa cena", "6,29 zł za miesiąc")]
    names = {f[0]: f[1] for f in FACTS}
    tiles = "".join(f'<a class="hl" href="/porownanie-vpn#{pid}"><span class="hlk">{k}</span><span class="hlv"><img src="{LOGOS[pid]}" alt="" width="26" height="26">{names[pid]}</span><span class="hld">{d}</span></a>'
                    for pid, k, d in items)
    return f'<div class="hls">{tiles}</div>'


def provblocks(full=True):
    out = ""
    for pid, name, url, pl, refund, dev, apps, src, srcname, note in FACTS:
        pr = PROFILE[pid]
        badge = f'<span class="badge">{pr["badge"]}</span>' if pr["badge"] else ""
        top = '<span class="badge gold">Nr 1 w rankingu</span>' if RANK[pid] == 1 else ""
        pros = "".join(f"<li>{CHECK}<span>{x}</span></li>" for x in pr["pros"])
        cons = "".join(f"<li>{MINUS}<span>{x}</span></li>" for x in pr["cons"])
        ps, pn = PRICE_SRC[pid]
        body = f"""  <div class="pbbody">
    <div><h4>Zalety</h4><ul class="pros">{pros}</ul></div>
    <div><h4>Wady</h4><ul class="cons">{cons}</ul></div>
    <div><h4>Cena i aplikacje</h4><p>{pr["terms"]}</p><p class="apps">{apps}</p>
      <p class="src">Źródła: <a href="{src}" target="_blank" rel="nofollow noopener">{srcname}</a>, <a href="{ps}" target="_blank" rel="nofollow noopener">{pn}</a>. Dane sprawdzone {CHECKED}, cena {PRICED}.</p></div>
  </div>""" if full else ""
        out += f"""<article class="pb" id="{pid}">
  <header class="pbh">
    <span class="rank" aria-label="Miejsce {RANK[pid]}">{RANK[pid]}</span>
    <img src="{LOGOS[pid]}" alt="" width="48" height="48">
    <div><h3>{name}{top}{badge}</h3><p>{pr["tag"]}</p></div>
    <div class="pbprice"><b>{pr["price"]}</b><span>{pr["unit"]}</span></div>
    <a class="btn big" {plink(pid, url)}>Zobacz ofertę {name}</a>{aff_note(pid)}
  </header>
  <div class="pbfacts">
    <div><span>Serwer w Polsce</span><b>{pl}</b></div>
    <div><span>Zwrot pieniędzy</span><b>{refund}</b></div>
    <div><span>Urządzenia jednocześnie</span><b>{dev}</b></div>
    <div><span>Punkty w rankingu</span><b>{sum(wpts(pid))} na {MAXPTS}</b></div>
  </div>
{body}
</article>"""
    return out


QUIZ = """<section class="quizsec"><div class="wrap narrowpad">
  <div class="quiz" id="quiz">
    <div class="qhead"><h2>Który VPN pasuje do Ciebie?</h2><p>Trzy pytania. Odpowiedź opiera się na faktach z tabeli, nie na reklamie.</p></div>
    <div class="qstep" data-q="pay"><h3>1. Chcesz płacić za VPN?</h3><div class="qopts">
      <button type="button" data-v="free">Nie, szukam darmowego</button><button type="button" data-v="paid">Tak, jeśli działa pewniej</button></div></div>
    <div class="qstep" data-q="dev" hidden><h3>2. Na ilu urządzeniach naraz?</h3><div class="qopts">
      <button type="button" data-v="1">Na jednym</button><button type="button" data-v="few">Od 2 do 10</button><button type="button" data-v="many">Więcej niż 10</button></div></div>
    <div class="qstep" data-q="prio" hidden><h3>3. Co jest dla Ciebie najważniejsze?</h3><div class="qopts">
      <button type="button" data-v="price">Najniższa cena</button><button type="button" data-v="pl">Dużo serwerów w Polsce</button><button type="button" data-v="refund">Długi czas na zwrot</button></div></div>
    <div class="qres" id="qres" hidden></div>
  </div>
</div></section>"""

DEVICES = """<section class="devsec"><div class="wrap">
  <div class="devtext">
    <h2>Na komputerze, telefonie i telewizorze</h2>
    <p>Wszyscy dostawcy z rankingu mają aplikacje na Windows, macOS, Linux, Android i iOS oraz na trzy główne platformy telewizyjne.</p>
    <ul class="devlist">
      <li><b>Android TV</b><span>Proton VPN, NordVPN, Surfshark, ExpressVPN, CyberGhost</span></li>
      <li><b>Apple TV</b><span>Proton VPN, NordVPN, Surfshark, ExpressVPN, CyberGhost</span></li>
      <li><b>Fire TV</b><span>Proton VPN, NordVPN, Surfshark, ExpressVPN, CyberGhost</span></li>
    </ul>
    <p class="muted small">Według stron dostawców, sprawdzone """ + CHECKED + """.</p>
  </div>
  <img class="devimg" src="/img/devices.webp" alt="" width="737" height="276" loading="lazy">
</div></section>"""

LOGOS = {"proton": "/logos/proton.svg", "protonfree": "/logos/proton.svg", "nord": "/logos/nord.svg", "surf": "/logos/surf.svg", "expr": "/logos/expr.svg", "cybr": "/logos/cyberghost-icon.png"}


def facts_table():
    rows = ""
    for pid, name, url, pl, refund, dev, tv, src, srcname, note in FACTS:
        rows += (f'<tr><td><a class="prov" href="#{pid}"><img src="{LOGOS[pid]}" alt="" width="30" height="30"><span>{name}</span></a></td>'
                 f'<td>{pl}</td><td>{refund}</td><td>{dev}</td><td>{tv}</td>'
                 f'<td><a class="btn" {plink(pid, url)}>Strona dostawcy</a>{aff_note(pid)}</td></tr>')
    return ('<div class="scrollx"><table class="facts"><thead><tr><th>Dostawca VPN</th><th>Serwer w Polsce</th><th>Zwrot pieniędzy</th>'
            '<th>Urządzenia jednocześnie</th><th>Aplikacje</th><th>Oferta</th></tr></thead><tbody>' + rows + '</tbody></table></div>')


def facts_sections():
    out = ""
    for pid, name, url, pl, refund, dev, tv, src, srcname, note in FACTS:
        out += f"""<div class="provsec" id="{pid}">
  <h3><img src="{LOGOS[pid]}" alt="" width="26" height="26"> {name}</h3>
  <dl class="kv">
    <dt>Nasz test</dt><dd data-prov-status="{pid}">{prov_status_html(pid)}</dd>
    <dt>Serwer w Polsce</dt><dd>{pl}</dd>
    <dt>Zwrot pieniędzy</dt><dd>{refund}</dd>
    <dt>Urządzenia jednocześnie</dt><dd>{dev}</dd>
    <dt>Aplikacje</dt><dd>{tv}</dd>
    <dt>Źródło danych</dt><dd><a href="{src}" target="_blank" rel="nofollow noopener">{srcname}</a>, sprawdzone {CHECKED}</dd>
  </dl>
  {f'<p class="muted">{note}</p>' if note else ''}
  <p><a class="btn" {plink(pid, url)}>Strona {name}</a>{aff_note(pid)}</p>
</div>"""
    return out


FLOWS.update({"tvpsport": flow("TVP Sport", ""), "free": flow("Polski serwis", ""), "tvpvod": flow("TVP VOD", "/logos/tvpvod.png"), "player": flow("Player", "/logos/player.svg"), "polsat": flow("Polsat Box Go", "/logos/polsat.svg")})

# ---------------------------------------------------------------- pages

PAGES = {}

PAGES["/"] = ("Polska telewizja za granicą i VPN | Polski Streaming",
              "Jak oglądać TVP VOD, Player i TVP Sport za granicą. Poradniki, porównanie VPN z cenami i codzienny test z prawdziwymi zrzutami ekranu.",
              home_hero()
              + bf_bar()
              + top3()
              + status_matrix()
              + guides_grid()
              + how_home()
              + faq([("Dlaczego polskie serwisy nie działają za granicą?", "Serwisy kupują prawa do filmów i transmisji tylko na Polskę. Sprawdzają Twój adres IP i blokują odtwarzanie spoza kraju."),
                     ("Czy wynik zależy od kraju, w którym mieszkam?", "Nie. Serwis widzi polski adres serwera VPN, a nie Twój adres. Od Twojego kraju zależy tylko prędkość połączenia."),
                     LEGAL_Q, FREE_Q, TV_Q,
                     ("Jak zarabia ta strona?", "Część linków na stronie to linki partnerskie. Dziś partnerami są __PARTNERS__: gdy kupisz przez nasz link, dostajemy prowizję, a Ty płacisz tyle samo. Prowizja nie daje punktów w rankingu i nie zmienia wyników testu.")]))

PAGES["/wyniki-testow"] = ("Wyniki testów VPN z polskimi serwisami | Polski Streaming",
    "Wyniki ostatniego testu, historia 30 dni i zrzuty ekranu: które VPN działają z TVP VOD, Playerem i TVP Sport.",
    band('<a href="/">Polska telewizja za granicą</a> / Wyniki testów', "Wyniki testów",
         f"Każdego ranka bot sprawdza, czy film gra przez VPN z serwerem w Polsce. Testujemy dziś: {tested_phrase()}.", WHEN)
    + RESULTS.replace('<a class="btn big" href="/porownanie-vpn">Zobacz ranking VPN</a>',
                      f'<div class="pcta"><a class="btn big" {plink("nord", "https://nordvpn.com")}>Zobacz ofertę NordVPN</a>{aff_note("nord")}<a class="more" href="/porownanie-vpn">Zobacz ranking 5 VPN</a></div>')
    + HISTORY + EVIDENCE)

PAGES["/tvp-vod-za-granica"] = ("Jak oglądać TVP VOD za granicą: test VPN | Polski Streaming",
    "TVP VOD za granicą: co działa bez VPN, co jest zablokowane, wynik codziennego testu i komunikaty błędów z rozwiązaniami.",
    band('<a href="/">Polska telewizja za granicą</a> / TVP VOD', "Jak oglądać TVP VOD za granicą",
         "TVP VOD jest darmowy, ale wiele materiałów działa tylko w Polsce. Sprawdzamy to codziennie na programie „Jeden z dziesięciu”.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>16 listopada 2026</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/tvpvod-test.webp", "vod.tvp.pl", "„Jeden z dziesięciu” gra przez VPN z polskim serwerem. Nasz test z 10.11.2026."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Część materiałów TVP VOD działa za granicą bez niczego. Reszta wymaga polskiego adresu IP, czyli VPN z serwerem w Polsce. To, czy film ruszy, zmienia się z dnia na dzień, dlatego niżej jest wynik naszego ostatniego testu.</p>

<h2>Dlaczego TVP VOD nie działa za granicą</h2>
<p>TVP kupuje prawa do wielu filmów, seriali i transmisji tylko na terytorium Polski. Serwis sprawdza adres IP urządzenia. Gdy adres jest zagraniczny, część materiałów się nie włącza.</p>
<p>Nie wszystko jest zablokowane. Własne produkcje TVP często działają także za granicą. W menu serwisu jest strona <a href="https://vod.tvp.pl/tvp-vod-za-granica" target="_blank" rel="noopener">TVP VOD za granicą</a>, na której można sprawdzić dostępność.</p>

<h2>Co jest w TVP VOD</h2>
<p>Lista z serwisu vod.tvp.pl, sprawdzona 10.11.2026:</p>
<ul>
  <li><b>Kanały na żywo:</b> TVP 1, TVP 2, TVP Info, TVP Kultura oraz kanały tematyczne, na przykład TVP Kryminały i TVP Klan.</li>
  <li><b>Seriale:</b> M jak miłość, Ojciec Mateusz, Na dobre i na złe, Klan, Barwy szczęścia, Komisarz Alex, Na sygnale.</li>
  <li><b>Programy:</b> Jeden z dziesięciu, The Voice of Poland, Rolnik szuka żony, Jaka to melodia?</li>
  <li><b>Filmy i klasyka:</b> Pan Tadeusz, Znachor, Pianista, Stawka większa niż życie, Czterdziestolatek.</li>
  <li><b>Działy:</b> Sport, Teatr, Dokumenty, Dla dzieci, News.</li>
</ul>

<h2>Trzy sposoby</h2>
<h3>1. Sprawdź, czy materiał działa bez VPN</h3>
<p>Otwórz program na vod.tvp.pl. Jeśli gra, nie potrzebujesz niczego więcej. Dotyczy to głównie produkcji własnych TVP.</p>
<h3>2. W Unii Europejskiej: zasada przenośności</h3>
<p>Unijne rozporządzenie 2017/1128 gwarantuje dostęp za granicą tylko do <b>płatnych</b> usług i tylko podczas czasowego pobytu. TVP VOD jest w większości darmowy, więc ta zasada go nie obowiązuje. Po Brexicie nie dotyczy też Wielkiej Brytanii (<a href="https://www.gov.uk/guidance/cross-border-portability-of-online-content-services-after-the-transition-period" target="_blank" rel="noopener">źródło: gov.uk</a>).</p>
<h3>3. VPN z serwerem w Polsce</h3>
<!--flow:tvpvod-->
<p>VPN daje Twojemu urządzeniu polski adres IP, więc TVP VOD widzi widza z Polski. To, czy film naprawdę ruszy, zależy od dostawcy VPN i od dnia.</p>
""", "prosec", brief([("Cena", "Darmowy, z reklamami"), ("Konto", "W teście niepotrzebne"), ("Reklamy przed filmem", "Około 3 minut"), ("Nasz test", "Codziennie, „Jeden z dziesięciu”")],
                     [("/porownanie-vpn", "Ranking VPN"), ("/wyniki-testow", "Wyniki testów"), ("/jak-testujemy", "Jak testujemy")]))
    + prose("""
<h2>Dziennik testu TVP VOD</h2>
<p>Test trwa od 10.11.2026. Bot otwiera najnowszy odcinek „Jeden z dziesięciu”. Nowy odcinek pojawia się w dni robocze: między 10 a 14 listopada bot przeszedł od odcinka 3643 do 3647. W weekend 14–15 listopada testował ten sam odcinek 3647, bo nowego nie było.</p>
<ul>
  <li><b>Reklamy są tu najdłuższe.</b> W udanych testach trwały od 133 do 191 sekund, zwykle około trzech minut. W Playerze i TVP Sport reklama trwa najwyżej około minuty.</li>
  <li><b>NordVPN</b> (w teście od 11.11.2026): film ruszył za pierwszym razem w każdym teście.</li>
  <li><b>Proton VPN Plus</b> (od 13.11.2026): działa. 15.11.2026 odtwarzacz za pierwszym razem pokazał błąd, po odświeżeniu film zagrał.</li>
  <li><b>Darmowy serwer Proton</b>: 10.11 i 13.11.2026 film nie ruszył w ciągu 330 sekund, a 15.11.2026 zatrzymał się po 51 sekundach.</li>
  <li><b>Obraz:</b> 1920 × 1080 we wszystkich udanych testach poza jednym (640 × 360, 10.11.2026). Ten program nie ma zabezpieczenia DRM.</li>
</ul>
<h3>Wyniki TVP VOD dzień po dniu</h3>
""" + svc_days("tvpvod", "Jeden wynik dziennie dla TVP VOD. Kreska: dostawcy nie było jeszcze w teście."), "prosec")
    + tested_cta("TVP VOD", "Te dwa płatne VPN sprawdzamy z TVP VOD każdego ranka. Surfsharka, ExpressVPN i CyberGhost jeszcze nie testujemy, są w <a href=\"/porownanie-vpn\">rankingu</a>.")
    + svc_result("tvpvod", "TVP VOD", "Bot włącza najnowszy odcinek programu „Jeden z dziesięciu” i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć TVP VOD przez VPN", "Kolejność ma znaczenie: najpierw VPN, potem strona.", [
        ("Połącz VPN z serwerem w Polsce", "Zrób to przed otwarciem strony. Jeśli strona była już otwarta, odśwież ją po połączeniu."),
        ("Otwórz vod.tvp.pl i kliknij „Akceptuję”", "Bez zgody w okienku prywatności reklamy się nie ładują, a wtedy film nie rusza."),
        ("Wybierz program i kliknij „Odtwórz”", "Przycisk jest pod tytułem programu. Serwis przeniesie Cię do najnowszego odcinka."),
        ("Poczekaj na koniec reklam", "W naszych testach trwały od 133 do 191 sekund. Nie odświeżaj strony w czasie reklam, bo zaczną się od nowa.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Program testowy", "„Jeden z dziesięciu”, najnowszy odcinek"),
        ("Czas reklam przed filmem", "133 do 191 sekund"),
        ("Jakość obrazu", "1920 × 1080, raz 640 × 360"),
        ("Zabezpieczenie DRM", "Nie, w tym programie"),
        ("Logowanie", "Nie było potrzebne"),
        ("Dni pomiarów", "Codziennie od 10.11.2026, stan na 16.11.2026")],
        "To są pomiary naszego bota, a nie dane producenta.")
    + errors_box(title="Błędy TVP VOD, które widzieliśmy", rows=[
        ("Wykryto wtyczkę adblock", "Reklamy się nie załadowały. Zdarza się, gdy VPN blokuje reklamy na poziomie DNS.", "Wyłącz w aplikacji VPN blokowanie reklam i odśwież stronę."),
        ("Wystąpił problem z materiałem. Spróbuj ponownie za chwilę", "Serwis nie podał filmu. W naszym teście ten sam serwer VPN godzinę wcześniej działał.", "Zmień serwer na inny polski albo spróbuj po kilku minutach."),
        ("Materiał niedostępny w Twoim kraju", "Serwis widzi zagraniczny adres IP.", "Sprawdź, czy VPN jest połączony z Polską, i odśwież stronę.")])
    + '<p class="note">Dwa pierwsze komunikaty widzieliśmy w naszych testach 10.11.2026. Trzeci to blokada regionalna. Opisujemy ją ze zrzutem ekranu na stronie <a href="/tvp-vod-material-niedostepny-w-twoim-kraju">TVP VOD: materiał niedostępny w Twoim kraju</a>.</p>',
    "prosec alt", shot("tvpvod", "TVP VOD"))
    + faq([("Czy potrzebuję konta w TVP VOD?", "W naszym teście „Jeden z dziesięciu” grał bez logowania. Część materiałów wymaga konta albo opłaty."),
           ("Czy TVP Sport działa tak samo?", "TVP Sport to osobny serwis (sport.tvp.pl) i testujemy go osobno. Wynik jest na stronie <a href=\"/wyniki-testow\">Wyniki testów</a>."),
           ("Czy mogę oglądać TVP VOD na telewizorze za granicą?", "Tak, jeśli telewizor albo przystawka ma aplikację VPN. TVP VOD ma aplikację na Android TV. Listę aplikacji każdego dostawcy VPN znajdziesz w <a href=\"/porownanie-vpn\">porównaniu</a>."),
           ("Czy wolno oglądać TVP VOD przez VPN?", "Sam VPN nie jest zabroniony w krajach Unii, w Wielkiej Brytanii ani w USA. Regulamin TVP VOD może jednak zabraniać omijania blokad regionalnych. Przeczytaj go, zanim zaczniesz.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/tvp-vod-za-granica", "TVP VOD")])

PAGES["/player-za-granica"] = ("Jak oglądać Player za granicą: test VPN | Polski Streaming",
    "Player za granicą: darmowe odcinki „BEZ OPŁAT”, pakiet Player International, wynik codziennego testu VPN i typowe błędy.",
    band('<a href="/">Polska telewizja za granicą</a> / Player', "Jak oglądać Player za granicą",
         "Player ma darmowe odcinki z reklamami i płatne pakiety. Sprawdzamy codziennie, czy darmowe „Fakty” grają przez VPN.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>16 listopada 2026</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/player-test.webp", "player.pl", "Darmowy odcinek „Faktów” w Playerze przez VPN, test z 10.11.2026."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Masz dwie drogi. Oficjalna to pakiet Player International, który działa bez VPN, ale nie obejmuje całej oferty. Druga to VPN z serwerem w Polsce: wtedy Player działa jak w kraju, a darmowe odcinki grają bez konta.</p>

<h2>Co jest w Playerze</h2>
<p>Stan ze strony player.pl, sprawdzony 10.11.2026:</p>
<ul>
  <li><b>Darmowe odcinki z etykietą „BEZ OPŁAT”.</b> Grają z reklamami i bez logowania. Są dostępne krótko: przy odcinkach „Faktów” widzieliśmy etykiety „ZNIKNIE W PONIEDZIAŁEK”.</li>
  <li><b>Programy i seriale TVN:</b> Fakty, Dzień Dobry TVN, Na Wspólnej, Chyłka, Hotel Paradise.</li>
  <li><b>Płatne działy w menu:</b> HBO, discovery+, Eurosport Pass, Canal+ oraz kanały na żywo.</li>
  <li><b>Wypożyczalnia</b> filmów płatnych osobno.</li>
</ul>

<h2>Co wybrać</h2>
<h3>1. Player International: oficjalna opcja</h3>
<p>To pakiet Playera dla widzów za granicą. Serwis opisuje go słowami „dostęp do twoich ulubionych kanałów TVN i VOD z zagranicy”. Działa bez VPN. Zakres i cenę sprawdź na stronie <a href="https://player.pl/playerplus/player-international" target="_blank" rel="noopener">Player International</a>, bo nie obejmuje całej oferty.</p>
<h3>2. Płatny pakiet podczas wyjazdu w Unii Europejskiej</h3>
<p>Jeśli płacisz za pakiet Playera w Polsce i wyjeżdżasz na krótko do innego kraju UE, rozporządzenie 2017/1128 daje Ci dostęp do Twojej subskrypcji. Nie dotyczy to stałego pobytu ani Wielkiej Brytanii.</p>
<h3>3. VPN z serwerem w Polsce</h3>
<!--flow:player-->
<p>Z polskim adresem IP Player zachowuje się tak jak w Polsce. To jedyny sposób na darmowe odcinki poza krajem.</p>
""", "prosec", brief([("Darmowe odcinki", "Tak, z etykietą „BEZ OPŁAT”"), ("Opcja oficjalna", "Player International"), ("Zabezpieczenie", "DRM, działa w Chrome"), ("Nasz test", "Codziennie, „Fakty”")],
                     [("/porownanie-vpn", "Ranking VPN"), ("/wyniki-testow", "Wyniki testów"), ("/jak-testujemy", "Jak testujemy")]))
    + prose("""
<h2>Dziennik testu Playera</h2>
<p>Test trwa od 10.11.2026. Bot otwiera listę odcinków „Faktów”, wybiera najnowszy z etykietą „BEZ OPŁAT” i włącza go bez logowania. Każdy odcinek jest chroniony DRM, a mimo to grał w zwykłym Chrome.</p>
<ul>
  <li><b>Reklama jest krótka:</b> od 25 do 56 sekund. Przez płatne serwery NordVPN i Proton od 13.11.2026 trwała 25–31 sekund.</li>
  <li><b>Jakość zależy od dostawcy VPN.</b> Przez Proton VPN Plus Player dawał obraz 960 × 540, przez NordVPN i darmowy serwer 640 × 360. To pomiar w przeglądarce bota, nie na telewizorze.</li>
  <li><b>NordVPN</b> (od 11.11.2026) i <b>Proton VPN Plus</b> (od 13.11.2026): ani jednego błędu w Playerze.</li>
  <li><b>Darmowy serwer Proton</b>: 10.11.2026 zamiast filmu był czarny ekran, a 14.11.2026 Player za pierwszym razem pokazał komunikat o blokowaniu reklam.</li>
</ul>
<h3>Wyniki Playera dzień po dniu</h3>
""" + svc_days("player", "Wynik Playera z porannego testu. Pusta kratka oznacza dzień przed dodaniem dostawcy."), "prosec")
    + tested_cta("Playerem", "Z darmowymi „Faktami” codziennie łączymy się przez te dwa płatne plany. Inni dostawcy są na razie tylko w <a href=\"/porownanie-vpn\">zestawieniu</a>, bez testu.")
    + svc_result("player", "Player", "Bot włącza najnowszy darmowy odcinek „Faktów” bez logowania i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć Player przez VPN", "Darmowe odcinki nie wymagają konta.", [
        ("Włącz VPN, wybierz Polskę", "Player sprawdza adres IP przy starcie filmu, więc VPN musi działać, zanim klikniesz „Oglądaj”."),
        ("Otwórz player.pl i kliknij „Akceptuję”", "Okienko zgody pojawia się przy pierwszej wizycie. Bez niej reklamy się nie włączą."),
        ("Wybierz odcinek z etykietą „BEZ OPŁAT”", "Odcinki bez tej etykiety wymagają płatnego pakietu i logowania."),
        ("Kliknij „Oglądaj” i poczekaj na reklamę", "W naszych testach reklama trwała od 25 do 56 sekund, potem ruszał odcinek.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Materiał testowy", "„Fakty”, najnowszy odcinek „BEZ OPŁAT”"),
        ("Czas reklam przed filmem", "25 do 56 sekund"),
        ("Jakość obrazu w teście", "640 × 360, przez Proton VPN Plus 960 × 540"),
        ("Zabezpieczenie DRM", "Tak"),
        ("Logowanie", "Nie było potrzebne"),
        ("Pomiary", "Każdego dnia od 10 listopada, ostatnia aktualizacja 16 listopada 2026")],
        "Jakość dotyczy przeglądarki bota. Na zwykłym komputerze może być wyższa, tego nie mierzyliśmy.")
    + errors_box(title="Błędy Playera i co z nimi zrobić", rows=[
        ("Wyłącz blokowanie reklam, aby oglądać", "Player nie dostał reklamy. U nas winny był serwer DNS dostawcy VPN.", "Wyłącz w aplikacji VPN blokowanie reklam albo zmień DNS i odśwież stronę."),
        ("Czarny ekran po kliknięciu „Oglądaj”", "Film się nie załadował. U nas druga próba po chwili zadziałała.", "Odśwież stronę. Jeśli to nie pomoże, zmień serwer VPN na inny polski."),
        ("Przekierowanie na stronę logowania", "Wybrany materiał jest w płatnym pakiecie.", "Wybierz odcinek „BEZ OPŁAT” albo zaloguj się na konto z pakietem.")])
    + '<p class="note">Testujemy darmową część Playera. Płatnych pakietów i Player International jeszcze nie testujemy. Ekran „Player jest niedostępny w Twojej lokalizacji” opisujemy <a href="/player-niedostepny-w-twojej-lokalizacji">na osobnej stronie</a>.</p>',
    "prosec alt", shot("player", "Player"))
    + faq([("Czym różni się Player International od VPN?", "Player International to płatny pakiet od Playera, legalny i bez VPN, ale z ograniczoną ofertą. Z VPN widzisz polską wersję serwisu, w tym darmowe odcinki."),
           ("Dlaczego darmowy odcinek zniknął?", "Darmowe odcinki są dostępne przez kilka dni. Przy „Faktach” serwis pokazuje etykietę z dniem, w którym odcinek zniknie."),
           ("Czy potrzebuję konta?", "Do odcinków „BEZ OPŁAT” nie. W naszym teście „Fakty” grały bez logowania."),
           ("Czy Player przez VPN jest zgodny z prawem?", "VPN jako narzędzie jest dozwolony w Unii, w Wielkiej Brytanii i w USA. Regulamin Playera może zabraniać omijania blokad regionalnych. Bez takiego ryzyka jest pakiet Player International.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/player-za-granica", "Player")])

PAGES["/tvp-sport-za-granica"] = ("Jak oglądać TVP Sport za granicą: test VPN | Polski Streaming",
    "TVP Sport za granicą: czym różnią się materiały wideo od transmisji na żywo, wynik codziennego testu VPN i liczby z naszych pomiarów.",
    band('<a href="/">Polska telewizja za granicą</a> / TVP Sport', "Jak oglądać TVP Sport za granicą",
         "TVP Sport jest darmowy i działa w przeglądarce. Za granicą część materiałów jest zablokowana. Sprawdzamy codziennie, czy wideo gra przez VPN.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>16 listopada 2026</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/tvpsport-test.webp", "sport.tvp.pl", "Materiał z działu Wideo na sport.tvp.pl, nasz test przez VPN z 10.11.2026."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Materiały wideo z TVP Sport grały w naszym teście przez VPN z serwerem w Polsce, bez konta i w pełnej jakości. Transmisji na żywo nie testujemy, a to one są najczęściej ograniczone licencją.</p>

<h2>Dwa rodzaje treści w TVP Sport</h2>
<p>Serwis sport.tvp.pl ma w menu osobne działy. Dla widza za granicą różnica między nimi jest ważna:</p>
<ul>
  <li><b>Wideo:</b> rozmowy, skróty i komentarze. To krótkie materiały własne TVP. Ten dział testujemy.</li>
  <li><b>Transmisje:</b> mecze i zawody na żywo. Prawa do nich TVP kupuje na Polskę, więc blokada regionalna dotyczy ich najczęściej.</li>
  <li><b>Retransmisje:</b> powtórki całych wydarzeń.</li>
</ul>
<p>W dniu sprawdzenia (10.11.2026) na liście transmisji były między innymi: Liga Narodów UEFA, Liga Mistrzyń, FIBA Europe Cup, NHL, Betclic 2 Liga i Igrzyska Olimpijskie Młodzieży.</p>

<h2>Jak oglądać</h2>
<h3>1. Najpierw spróbuj bez VPN</h3>
<p>Otwórz materiał i sprawdź, czy rusza. W naszym teście z USA (11.11.2026) wideo było zablokowane, a z krajów Unii jeszcze nie sprawdzaliśmy. Jak wygląda blokada, pokazujemy na stronie <a href="/tvp-sport-material-niedostepny">TVP Sport: materiał niedostępny</a>.</p>
<h3>2. VPN z serwerem w Polsce</h3>
<!--flow:tvpsport-->
<p>Gdy materiał jest zablokowany, polski adres IP z VPN zwykle wystarcza. W naszym teście wideo ruszyło za pierwszym razem także wtedy, gdy TVP VOD przez ten sam serwer nie działał.</p>
<h3>3. Transmisje na żywo</h3>
<p>Nie mamy jeszcze wyniku testu dla transmisji na żywo. Jeśli zależy Ci na konkretnym meczu, sprawdź połączenie wcześniej na innej transmisji i miej w zapasie drugi polski serwer.</p>
""", "prosec", brief([("Cena", "Darmowy, z reklamami"), ("Konto", "W teście niepotrzebne"), ("Reklamy przed wideo", "Zwykle poniżej minuty"), ("Nasz test", "Codziennie, najnowsze wideo")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/wyniki-testow", "Wyniki testów"), ("/porownanie-vpn", "Porównanie VPN")]))
    + prose("<h3>Wyniki TVP Sport dzień po dniu</h3><p>Od 13.11.2026 materiał wideo zagrał przez każdy testowany serwer, także darmowy. Bot co dzień bierze inny, najnowszy materiał.</p>" + svc_days("tvpsport", "TVP Sport, jeden materiał dziennie. „—” przed datą dodania dostawcy do testu."), "prosec")
    + tested_cta("TVP Sport", "Wideo z TVP Sport bot włącza każdego dnia przez oba płatne plany. Pozostałe VPN opisujemy w <a href=\"/porownanie-vpn\">rankingu</a> tylko na podstawie danych ze stron firm.")
    + svc_result("tvpsport", "TVP Sport", "Bot otwiera dział „Wideo”, wybiera najnowszy materiał dłuższy niż 80 sekund i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć wideo z TVP Sport przez VPN", "Odtwarzacz jest na stronie artykułu, pod tytułem.", [
        ("Najpierw polski serwer VPN", "Połącz się, zanim otworzysz sport.tvp.pl."),
        ("Otwórz sport.tvp.pl i kliknij „Akceptuję”", "Okienko zgody zasłania stronę przy pierwszej wizycie."),
        ("Wejdź w dział „Wideo” i wybierz materiał", "Materiały wideo mają w tytule dopisek [WIDEO]."),
        ("Kliknij przycisk odtwarzania na obrazie", "Najpierw lecą reklamy. W naszych testach trwały od 10 do 71 sekund.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Materiał testowy", "Najnowsze wideo z działu „Wideo”"),
        ("Czas reklam przed wideo", "10 do 71 sekund"),
        ("Jakość obrazu", "1920 × 1080"),
        ("Zabezpieczenie DRM", "Nie"),
        ("Logowanie", "Nie było potrzebne"),
        ("Dni pomiarów", "Codziennie od 10.11.2026, stan na 16.11.2026")],
        "To są pomiary naszego bota. Dotyczą materiałów wideo, a nie transmisji na żywo.")
    + '<p class="note">TVP Sport był w naszych testach najbardziej stabilny z trzech serwisów: działał w obu uruchomieniach, także gdy TVP VOD pokazywał błąd.</p>',
    "prosec alt", shot("tvpsport", "TVP Sport"))
    + faq([("Czy transmisje na żywo z TVP Sport działają przez VPN?", "Tego jeszcze nie testujemy. Testujemy materiały z działu „Wideo”. Transmisje mają osobne licencje i mogą zachowywać się inaczej."),
           ("Czy TVP Sport to to samo co TVP VOD?", "Nie. To dwa osobne serwisy z osobnymi odtwarzaczami. Dlatego testujemy je osobno i wyniki bywają różne."),
           ("Czy potrzebuję konta?", "W naszym teście materiały wideo grały bez logowania.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/tvp-sport-za-granica", "TVP Sport")])

PAGES["/darmowy-vpn-polska-telewizja"] = ("Darmowy VPN do polskiej telewizji: test | Polski Streaming",
    "Czy darmowy VPN wystarczy do TVP VOD i Playera? Wynik codziennego testu darmowego serwera w Polsce i instrukcja ustawienia krok po kroku.",
    band('<a href="/">Polska telewizja za granicą</a> / Darmowy VPN', "Darmowy VPN do polskiej telewizji: czy to działa?",
         "Testujemy codziennie darmowy serwer w Polsce. Krótko: czasem działa, czasem nie, a ustawienie wymaga jednego obejścia.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>', image="gift")
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Tak, da się oglądać polskie serwisy przez darmowy VPN, ale nie codziennie. W naszych testach ten sam darmowy serwer rano odtwarzał TVP VOD i Playera, a w południe już nie. Jeśli oglądasz od czasu do czasu, wystarczy. Jeśli chcesz mieć pewność przed meczem, nie.</p>

<h2>Który darmowy VPN ma serwer w Polsce</h2>
<p>Testujemy Proton VPN w planie darmowym, bo ma darmowy serwer w Polsce (PL-FREE#1). Innych darmowych VPN nie sprawdzaliśmy, więc o nich nie piszemy.</p>
<p>Ograniczenia planu darmowego według <a href="https://protonvpn.com/pricing" target="_blank" rel="nofollow noopener">cennika Proton VPN</a> (sprawdzone 10.11.2026): jedno urządzenie naraz i serwery w 10 krajach, przy czym kraj wybiera aplikacja.</p>

<h2>Problem: aplikacja sama wybiera kraj</h2>
<p>W darmowym planie nie wskażesz Polski w aplikacji. Aplikacja połączy Cię z jednym z 10 krajów i może to być na przykład Holandia. Wtedy polskie serwisy dalej widzą zagraniczny adres.</p>
<p>Obejście: w panelu konta Proton można pobrać plik konfiguracji WireGuard dla konkretnego darmowego serwera, także polskiego. Tak właśnie łączy się nasz bot.</p>
<!--flow:free-->

<h2>Co pokazały nasze testy</h2>
<p>Jednego dnia (10.11.2026) uruchomiliśmy test kilka razy przez ten sam darmowy serwer:</p>
<ul>
  <li><b>Rano:</b> TVP VOD i Player grały 60 sekund bez przerwy, cztery razy z rzędu.</li>
  <li><b>W południe:</b> Player pokazał czarny ekran, a druga próba zadziałała.</li>
  <li><b>Pół godziny później:</b> TVP VOD dwa razy pokazał błąd „Wystąpił problem z materiałem”. TVP Sport w tym samym czasie działał.</li>
  <li><b>Prędkość pobierania:</b> od 51 do 157 Mb/s, zależnie od pory i miejsca pomiaru.</li>
</ul>
<p>W panelu Proton serwer PL-FREE#1 pokazywał tego dnia obciążenie 100%. To prawdopodobna przyczyna wahań, ale nie mamy na to dowodu.</p>
""", "prosec", brief([("Testowany VPN", "Proton VPN, plan darmowy"), ("Serwer", "PL-FREE#1, Warszawa"), ("Urządzenia", "1 naraz"), ("Wynik", "Zmienny, zobacz historię")],
                     [("/wyniki-testow", "Wyniki testów i historia"), ("/porownanie-vpn", "Porównanie z płatnymi VPN"), ("/jak-testujemy", "Jak testujemy")]))
    + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Wynik ostatniego testu darmowego serwera</h2><p>Ten sam serwer, trzy serwisy, codziennie rano.</p></div>
  <div class="svc lastbox" data-last>{last_rows_html("plan darmowy")}</div>
  <p class="after"><a href="/wyniki-testow">Historia 30 dni i zrzuty ekranu</a></p>
</div></section>"""
    + steps("Jak ustawić darmowy serwer w Polsce", "Potrzebujesz darmowego konta Proton i aplikacji WireGuard.", [
        ("Załóż darmowe konto Proton VPN", "Wystarczy adres e-mail. Karta nie jest potrzebna."),
        ("W panelu konta otwórz „Pobieranie”", "Na dole strony jest część „Konfiguracja WireGuard”. Wpisz dowolną nazwę i wybierz swój system."),
        ("Wybierz darmowy serwer w Polsce", "Zaznacz konfigurację dla serwerów darmowych, rozwiń „Polska” i kliknij „Utwórz” przy PL-FREE. Pobierz plik .conf."),
        ("Zmień linię DNS w pliku", "Otwórz plik w notatniku i zamień wartość DNS na 1.1.1.1. Bez tego TVP VOD i Player pokazują komunikat o adblocku."),
        ("Zaimportuj plik do aplikacji WireGuard", "Darmowa aplikacja WireGuard jest na Windows, macOS, Android i iOS. Włącz tunel i otwórz serwis.")])
    + prose("""
<h2>Dlaczego zmiana DNS jest konieczna</h2>
<p>Pobrany plik ma wpisany serwer DNS dostawcy. W naszych testach ten serwer blokował domeny reklamowe. TVP VOD pokazywał wtedy „Wykryto wtyczkę adblock”, a Player „Wyłącz blokowanie reklam, aby oglądać”. Po zmianie DNS na neutralny (1.1.1.1) oba serwisy ruszyły. Plik zawiera Twój klucz prywatny, więc nie wysyłaj go nikomu.</p>

<h2>Kiedy darmowy VPN wystarczy, a kiedy nie</h2>
<ul>
  <li><b>Wystarczy,</b> gdy oglądasz od czasu do czasu, na jednym urządzeniu, i możesz spróbować ponownie za godzinę.</li>
  <li><b>Nie wystarczy,</b> gdy chcesz oglądać na telewizorze bez komputera, na kilku urządzeniach albo o konkretnej godzinie.</li>
</ul>
<p>Płatne plany mają więcej polskich serwerów, więc gdy jeden nie działa, można przełączyć się na inny. Których płatnych VPN jeszcze nie przetestowaliśmy, widać w <a href="/porownanie-vpn">porównaniu</a>.</p>
<p class="note">Ta strona opisuje nasze własne testy jednego darmowego serwera. Nie jest to ocena całej usługi Proton VPN.</p>
""", "prosec alt")
    + faq([("Czy darmowy VPN jest bezpieczny?", "To zależy od dostawcy. Opisujemy tylko ten, którego sami używamy w testach. Nie instaluj nieznanych darmowych aplikacji VPN tylko dlatego, że obiecują polski serwer."),
           ("Dlaczego w aplikacji Proton nie widzę Polski?", "W planie darmowym aplikacja sama wybiera kraj. Polski serwer ustawisz tylko przez plik konfiguracji WireGuard z panelu konta."),
           ("Czy to działa na telewizorze?", "Trudno. Plan darmowy to jedno urządzenie, a plik WireGuard trzeba zaimportować ręcznie. Najprościej oglądać na komputerze albo telefonie.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/darmowy-vpn-polska-telewizja", "Darmowy VPN")])

SRC_DESTATIS = '<a href="https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Migration-Integration/Tabellen/auslaendische-bevoelkerung-staatsangehoerigkeit-jahre.html" target="_blank" rel="nofollow noopener">Destatis</a>'
SRC_KOS = '<a href="https://en.kingofsat.net/find2.php?cl=pol&amp;num_pos=13.0E&amp;ordre=freq&amp;standard=All&amp;filtre=Clear" target="_blank" rel="nofollow noopener">lista KingOfSat</a>'
SRC_TELEKOM = '<a href="https://www.telekom.de/shop/option/tv-paket-polski/tv-option" target="_blank" rel="nofollow noopener">telekom.de</a>'
SRC_VODAFONE = '<a href="https://www.vodafone.de/privat/fernsehen/tv-optionen/tv-international/polnisch.html" target="_blank" rel="nofollow noopener">vodafone.de</a>'
SRC_PLAYERINT = '<a href="https://promocja.player.pl/zobacz-wiecej-player-international" target="_blank" rel="nofollow noopener">strona Player International</a>'
SRC_POLONIA = '<a href="https://polsatboxgo.pl/pakiety/world" target="_blank" rel="nofollow noopener">stronie pakietu</a>'
SRC_TVPFAQ = '<a href="https://vod.tvp.pl/faq" target="_blank" rel="nofollow noopener">vod.tvp.pl/faq</a>'

PAGES["/polska-telewizja-w-niemczech"] = ("Polska telewizja w Niemczech: 5 sposobów i ceny | Polski Streaming",
    "Polska telewizja w Niemczech: darmowe kanały z satelity, pakiety Vodafone i Telekom z cenami, Player International, Polsat Box Go i VPN.",
    band('<a href="/">Polska telewizja za granicą</a> / Niemcy', "Polska telewizja w Niemczech",
         "Pięć sposobów na polskie kanały w Niemczech: od darmowej satelity po VPN. Z cenami w euro i źródłami.",
         f'<div class="when mono">{BYLINE}<span>Ceny i dane sprawdzone: <b>11.11.2026</b></span></div>', image="europe")
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Za darmo masz TVP Polonia i kilkanaście innych polskich kanałów z satelity Hot Bird. Pakiet polski u operatora kosztuje od 4,94 € za miesiąc. TVP1, TVP2, Polsatu i TVN w wersji krajowej nie ma w żadnej niemieckiej ofercie. Do nich prowadzą polskie serwisy internetowe, a za granicą część ich treści jest zablokowana.</p>

<p>W Niemczech mieszka 839 660 obywateli Polski (stan na 31.12.2025, __DESTATIS__). To największa grupa Polaków w Unii Europejskiej poza Polską.</p>

<h2>Porównanie pięciu sposobów</h2>
<div class="scrollx keep"><table class="mini3"><thead><tr><th>Sposób</th><th>Co dostajesz</th><th>Cena</th></tr></thead><tbody>
<tr><td>Satelita Hot Bird 13°E</td><td>TVP Polonia, TVP World, Polonia 1, Tele 5 i inne kanały niekodowane</td><td>0 € za miesiąc, potrzebna antena</td></tr>
<tr><td>Telekom MagentaTV, pakiet „Polski”</td><td>ITVN, TVP Polonia</td><td>4,94 € za miesiąc</td></tr>
<tr><td>Vodafone, „TV International Polnisch”</td><td>TVP Polonia, ITVN, ITVN Extra HD, TVN24 HD, iTVS</td><td>8,99 € za miesiąc</td></tr>
<tr><td>Player International</td><td>Biblioteka Playera bez reklam, ITVN, ITVN Extra, TVN24</td><td>50 zł za 30 dni</td></tr>
<tr><td>VPN z serwerem w Polsce</td><td>Polska wersja serwisów: TVP VOD, Player, TVP Sport</td><td>od 6,29 zł za miesiąc</td></tr>
</tbody></table></div>

<h2>1. Satelita: polskie kanały za darmo</h2>
<p>Z satelity Hot Bird (13°E) odbierzesz w Niemczech polskie kanały bez abonamentu i bez karty. Na liście kanałów niekodowanych są dziś między innymi:</p>
<ul>
  <li><b>TVP Polonia</b> i <b>TVP World</b> (ten drugi po angielsku),</li>
  <li><b>Polonia 1</b>, <b>Tele 5</b>, <b>TVS</b> i <b>Kanał Zero TV</b>,</li>
  <li>kanały muzyczne: Nuta TV, Nuta Gold, Power TV, Szlagier TV, 4Fun.</li>
</ul>
<p>Źródło: __KINGOFSAT__, sprawdzone 11.11.2026. TVP1, TVP2, Polsatu i TVN nie ma na tej liście. Te kanały są na satelicie zakodowane.</p>
<p>Potrzebujesz czaszy skierowanej na 13°E i dekodera albo telewizora z tunerem DVB-S2. W mieszkaniu na wynajem zapytaj najpierw właściciela o zgodę na antenę.</p>

<h2>2. Pakiet polski u niemieckiego operatora</h2>
<p>To najprostsza droga, jeśli masz już telewizję od Telekomu albo Vodafone. Kanały włączasz jako dodatek do umowy.</p>
<ul>
  <li><b>Telekom MagentaTV, „TV-Paket Polski”:</b> ITVN i TVP Polonia. 4,94 € za miesiąc, bez minimalnego okresu umowy, wypowiedzenie z miesięcznym terminem. Źródło: __TELEKOM__.</li>
  <li><b>Vodafone, „TV International Polnisch”:</b> TVP Polonia, ITVN, ITVN Extra HD, TVN24 HD, iTVS i Radio Zet. 8,99 € za miesiąc, umowa na 12 miesięcy i 19,99 € opłaty jednorazowej. Potrzebna jest usługa GigaTV. Źródło: __VODAFONE__.</li>
</ul>
<p>ITVN i TVP Polonia to kanały przygotowane dla widzów za granicą. Mają inny program niż TVN i TVP1 w Polsce. Nie znajdziesz w nich wszystkich seriali i transmisji sportowych.</p>

<h2>3. Polskie serwisy z ofertą dla zagranicy</h2>
<h3>Player International</h3>
<p>Pakiet kosztuje 50 zł za 30 dni i ma 7 dni okresu próbnego. Obejmuje bibliotekę Playera bez reklam oraz trzy kanały na żywo: ITVN, ITVN Extra i TVN24. Zapłacisz kartą polską albo zagraniczną. Oferta różni się od pakietów sprzedawanych w Polsce. Źródło: __PLAYERINT__. Więcej w poradniku <a href="/player-za-granica">Player za granicą</a>.</p>
<h3>Polsat Box Go, pakiet Polonia</h3>
<p>Polsat ma pakiet dla osób mieszkających za granicą. Według strony pakietu jest w nim 18 kanałów, między innymi Polsat 1 i Polsat News, a zawartość może zależeć od kraju. Aktualną cenę sprawdź na __POLONIA__, bo nie udało nam się jej potwierdzić. Więcej w poradniku <a href="/polsat-box-go-za-granica">Polsat Box Go za granicą</a>.</p>
<h3>TVP VOD</h3>
<p>Część materiałów TVP VOD działa w Niemczech bez żadnych dodatków. W dziale pytań i odpowiedzi serwis pisze: „Ze względów licencyjnych niektóre treści są dostępne tylko dla użytkowników na terytorium Polski” (__TVPFAQ__). Więcej w poradniku <a href="/tvp-vod-za-granica">TVP VOD za granicą</a>.</p>

<h2>4. Masz polski abonament i jesteś w Niemczech czasowo</h2>
<p>Unijne rozporządzenie 2017/1128 pozwala korzystać z <b>płatnych</b> usług kupionych w kraju zamieszkania podczas czasowego pobytu w innym państwie Unii. Dotyczy to osób, które mieszkają w Polsce i wyjechały na jakiś czas, na przykład do pracy sezonowej.</p>
<ul>
  <li><b>Polsat Box Go</b> włącza dostęp w całej Unii po podaniu numeru telefonu zarejestrowanego u polskiego operatora.</li>
  <li><b>TVP VOD</b> udostępnia płatne treści użytkownikowi zalogowanemu, który mieszka na stałe w Polsce i przebywa czasowo w innym państwie.</li>
</ul>
<p>Jeśli mieszkasz w Niemczech na stałe, ta zasada Cię nie obejmuje. Nie obejmuje też treści darmowych.</p>

<h2>5. VPN z serwerem w Polsce</h2>
<p>VPN daje Ci polski adres IP. Serwis traktuje Cię wtedy jak widza w Polsce i pokazuje krajową wersję, także darmowe odcinki z reklamami. To jedyny z pięciu sposobów, który prowadzi do polskiej wersji TVP VOD, Playera i TVP Sport.</p>
<p>Są dwa zastrzeżenia. Serwisy blokują część adresów VPN, więc żaden dostawca nie da gwarancji. Regulamin serwisu może też zabraniać omijania blokad regionalnych. Samo używanie VPN jest w Niemczech legalne.</p>
<p>Każdego ranka sprawdzamy botem, czy trzy polskie serwisy grają przez VPN z serwerem w Polsce. Aktualne wyniki są na stronie <a href="/wyniki-testow">Wyniki testów</a>.</p>

<h2>Sport: skoki narciarskie i mecze</h2>
<p>Niemcy i Polska mają ten sam czas, więc transmisje na żywo są o tej samej godzinie.</p>
<ul>
  <li><b>Skoki narciarskie 2026/27:</b> w Niemczech pokazują je ARD, ZDF i Eurosport, z niemieckim komentarzem. ARD i ZDF są bezpłatne. Sezon zaczyna się w Lillehammer 20 listopada 2026.</li>
  <li><b>Polski komentarz:</b> jest w TVP Sport. Transmisje na żywo mają osobne licencje i za granicą bywają zablokowane. Materiały wideo z TVP Sport grały w naszym teście przez VPN. Szczegóły w poradniku <a href="/tvp-sport-za-granica">TVP Sport za granicą</a>.</li>
</ul>

<h2>Co zobaczysz, gdy serwis Cię zablokuje</h2>
<p>To są komunikaty z polskich serwisów dla widza z zagranicznym adresem IP:</p>
<ul>
  <li><b>TVP VOD:</b> „Z powodów licencyjnych materiał jest niedostępny w Twoim kraju.” <a href="/tvp-vod-material-niedostepny-w-twoim-kraju">Co zrobić</a></li>
  <li><b>TVP Sport:</b> „Przepraszamy. Z uwagi na ograniczenia licencyjne materiał jest niedostępny w kraju z którego się łączysz.” <a href="/tvp-sport-material-niedostepny">Co zrobić</a></li>
  <li><b>Player:</b> „Ups... Player jest niedostępny w Twojej lokalizacji”. <a href="/player-niedostepny-w-twojej-lokalizacji">Co zrobić</a></li>
</ul>
<p>Komunikat nie oznacza awarii. Oznacza, że serwis rozpoznał adres spoza Polski.</p>
""".replace("__DESTATIS__", SRC_DESTATIS).replace("__KINGOFSAT__", SRC_KOS).replace("__TELEKOM__", SRC_TELEKOM).replace("__VODAFONE__", SRC_VODAFONE)
   .replace("__PLAYERINT__", SRC_PLAYERINT).replace("__POLONIA__", SRC_POLONIA).replace("__TVPFAQ__", SRC_TVPFAQ),
    "prosec", brief([("Za darmo", "Satelita Hot Bird 13°E"), ("Najtańszy pakiet", "4,94 € (Telekom)"), ("TVP1, TVP2, Polsat, TVN", "Tylko przez polskie serwisy"), ("Ceny sprawdzone", "11.11.2026")],
                     [("/polska-telewizja-w-uk", "Polska telewizja w UK"), ("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/porownanie-vpn", "Ranking VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + faq([("Czy w Niemczech da się oglądać TVP1 i TVP2 na żywo?", "Nie ma ich w ofertach niemieckich operatorów ani wśród niekodowanych kanałów na satelicie Hot Bird. Programy TVP są w serwisie TVP VOD, a za granicą część z nich jest zablokowana."),
           ("Ile kosztuje polska telewizja w Niemczech?", "Kanały niekodowane z satelity są bezpłatne. Pakiet polski w Telekom MagentaTV kosztuje 4,94 € za miesiąc, a w Vodafone 8,99 € za miesiąc. Player International kosztuje 50 zł za 30 dni."),
           ("Czy Rundfunkbeitrag obejmuje polskie kanały?", "Nie. Rundfunkbeitrag finansuje niemieckie media publiczne: ARD, ZDF i Deutschlandradio. Za polskie pakiety płacisz osobno."),
           ("Czy VPN jest w Niemczech legalny?", "Tak, używanie VPN jest legalne. Regulamin serwisu streamingowego może jednak zabraniać omijania blokad regionalnych. Przeczytaj regulamin swojego serwisu."),
           ("Co jest lepsze: pakiet operatora czy VPN?", "Pakiet operatora działa na telewizorze bez ustawień, ale daje kanały w wersji dla zagranicy. VPN prowadzi do krajowej wersji serwisów, ale wymaga aplikacji i nie daje gwarancji działania.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/polska-telewizja-w-niemczech", "Polska telewizja w Niemczech")])

def errwhen():
    return f'<div class="when mono">{BYLINE}<span>Test bez VPN: <b>11.11.2026, z USA</b></span></div>'


PAGES["/tvp-vod-material-niedostepny-w-twoim-kraju"] = ("TVP VOD: „materiał jest niedostępny w Twoim kraju”. Co zrobić | Polski Streaming",
    "Co oznacza komunikat TVP VOD „Z powodów licencyjnych materiał jest niedostępny w Twoim kraju”, kiedy się pojawia i jakie masz wyjścia. Ze zrzutem ekranu z naszego testu.",
    band('<a href="/">Polska telewizja za granicą</a> / <a href="/tvp-vod-za-granica">TVP VOD</a> / Komunikat', "TVP VOD: „materiał jest niedostępny w Twoim kraju”",
         "Ten komunikat to blokada regionalna, a nie awaria. Pokazujemy, jak wygląda, skąd się bierze i co możesz zrobić.",
         errwhen(), figure=frame("/img/blok-tvpvod.webp", "vod.tvp.pl", "Zrzut ekranu z naszego testu bez VPN, 11.11.2026, adres IP z USA."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> TVP VOD rozpoznał, że łączysz się spoza Polski, a ten materiał ma licencję tylko na Polskę. Z przeglądarką, kontem ani telewizorem wszystko jest w porządku. Wyjścia są trzy: inny materiał, zalogowanie na konto z pakietem TVP+ podczas pobytu w Unii albo polski adres IP z VPN.</p>

<h2>Jak wygląda komunikat</h2>
<p>11 listopada 2026 otworzyliśmy TVP VOD z komputera w USA, bez VPN. Strona programu „Jeden z dziesięciu” załadowała się normalnie, razem z listą odcinków. Dopiero po kliknięciu odcinka 3644 odtwarzacz pokazał na czarnym tle:</p>
<blockquote>Z powodów licencyjnych materiał jest niedostępny w Twoim kraju.<br><br>Przepisy UE pozwalają abonentom, którzy w kraju zamieszkania (w tym przypadku w PL) zakupili pakiet TVP + utrzymać dostęp do materiałów wchodzących w skład pakietu, w czasie wizyty w innym kraju UE.</blockquote>
<p>Pod spodem jest jeden przycisk: „Zamknij”. Film nie rusza, nie ma też reklam przed filmem.</p>

<h2>Dlaczego TVP VOD blokuje za granicą</h2>
<p>Telewizja kupuje prawa do filmów, seriali i teleturniejów na określony kraj. Serwis sprawdza Twój adres IP przy starcie odtwarzania. Gdy adres jest spoza Polski, a licencja obejmuje tylko Polskę, odtwarzacz pokazuje ten komunikat zamiast filmu.</p>
<p>Blokada dotyczy pojedynczego materiału, a nie całego serwisu. Dlatego strona, opisy i listy odcinków działają, a inny program może się odtworzyć bez problemu.</p>

<h2>Inne komunikaty TVP VOD o lokalizacji</h2>
<p>W tekstach serwisu są jeszcze trzy komunikaty z tej samej grupy. Tych nie widzieliśmy w naszym teście:</p>
<div class="scrollx keep"><table class="mini3"><thead><tr><th>Komunikat</th><th>Co oznacza</th></tr></thead><tbody>
<tr><td>„Łączysz się spoza Polski”</td><td>Ogólne ostrzeżenie: część materiałów może być niedostępna w Twojej lokalizacji. Serwis odsyła do strony VOD International.</td></tr>
<tr><td>„Ze względu na ograniczenia licencyjne wybrany materiał możesz oglądać tylko na terenie Polski i innych krajów UE”</td><td>Materiał działa w Unii, ale nie poza nią.</td></tr>
<tr><td>„Transgraniczność aktywna” albo „Transgraniczność nieaktywna”</td><td>Etykieta przy koncie. Pokazuje, czy masz włączony dostęp do płatnych treści w innych krajach Unii.</td></tr>
</tbody></table></div>

<h2>Co możesz zrobić</h2>
<h3>1. Sprawdź inny materiał</h3>
<p>Licencje są różne dla różnych programów. Własne produkcje TVP częściej działają za granicą niż filmy i formaty kupione od innych firm.</p>
<h3>2. Mieszkasz w Polsce i masz pakiet TVP+</h3>
<p>Zaloguj się. Według komunikatu i unijnego rozporządzenia 2017/1128 pakiet ma działać podczas wizyty w innym kraju Unii. Ta zasada nie obejmuje krajów spoza Unii, na przykład USA i Wielkiej Brytanii. Nie obejmuje też treści darmowych.</p>
<h3>3. Połącz się przez VPN z serwerem w Polsce</h3>
<p>Z polskim adresem IP serwis traktuje Cię jak widza w kraju. Ten sam program, „Jeden z dziesięciu”, sprawdzamy codziennie przez VPN z serwerem w Polsce. Wynik z każdego dnia jest w poradniku <a href="/tvp-vod-za-granica">TVP VOD za granicą</a>.</p>

<h2>Komunikat jest, mimo że VPN jest włączony</h2>
<ul>
  <li><b>VPN połączył się z innym krajem.</b> Aplikacje często wybierają najszybszy serwer, a nie polski. W darmowym planie Proton VPN aplikacja w ogóle nie pozwala wskazać Polski.</li>
  <li><b>Strona była otwarta przed połączeniem.</b> Odśwież ją po włączeniu VPN.</li>
  <li><b>Przeglądarka zdradza lokalizację.</b> Odmów stronie dostępu do lokalizacji, jeśli o nią pyta.</li>
</ul>
<p>Gdy TVP VOD przez VPN pokazuje inny tekst, na przykład „Wystąpił problem z materiałem”, to nie jest blokada regionalna. Ten przypadek opisujemy w poradniku TVP VOD.</p>
""", "prosec", brief([("Rodzaj błędu", "Blokada regionalna"), ("Kiedy się pojawia", "Po kliknięciu odcinka"), ("Nasz test", "USA, bez VPN, 11.11.2026"), ("Program w teście", "Jeden z dziesięciu")],
                     [("/tvp-vod-za-granica", "Poradnik: TVP VOD za granicą"), ("/tvp-sport-material-niedostepny", "Ten sam problem w TVP Sport"), ("/porownanie-vpn", "Ranking VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + faq([("Czy komunikat oznacza, że moje konto jest zablokowane?", "Nie. Komunikat dotyczy adresu IP i jednego materiału. Konto działa normalnie."),
           ("Czy zmiana przeglądarki albo wyczyszczenie ciasteczek pomoże?", "Nie. Serwis sprawdza adres IP, a ten jest taki sam w każdej przeglądarce."),
           ("Czy w Niemczech albo Holandii jest tak samo?", "Nasz test był z USA. W krajach Unii działa dodatkowo zasada dla abonentów pakietu TVP+, ale treści darmowe mogą być zablokowane tak samo."),
           ("Czy TVP VOD ma ofertę dla widzów za granicą?", "Serwis odsyła w jednym z komunikatów do strony VOD International. Nie sprawdzaliśmy jeszcze, co ona zawiera.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/tvp-vod-za-granica", "TVP VOD"), ("/tvp-vod-material-niedostepny-w-twoim-kraju", "Materiał niedostępny w Twoim kraju")])

PAGES["/player-niedostepny-w-twojej-lokalizacji"] = ("„Player jest niedostępny w Twojej lokalizacji”: co zrobić | Polski Streaming",
    "Komunikat „Ups... Player jest niedostępny w Twojej lokalizacji”: kiedy się pojawia, czym różni się od blokady jednego odcinka i jakie masz wyjścia.",
    band('<a href="/">Polska telewizja za granicą</a> / <a href="/player-za-granica">Player</a> / Komunikat', "„Player jest niedostępny w Twojej lokalizacji”",
         "Poza Unią Europejską Player zamyka cały serwis, a nie jeden odcinek. Pokazujemy, jak to wygląda i co da się z tym zrobić.",
         errwhen(), figure=frame("/img/blok-player.webp", "player.pl/international", "Zrzut ekranu z naszego testu bez VPN, 11.11.2026, adres IP z USA. Adres IP na dole ekranu zakryliśmy."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Player sprawdził Twój adres IP i uznał, że jesteś w kraju, w którym serwis nie działa. W naszym teście z USA nie otworzyła się żadna podstrona. Zostają dwie drogi: pakiet Player International, jeśli jest sprzedawany w Twoim kraju, albo polski adres IP z VPN.</p>

<h2>Jak wygląda komunikat</h2>
<p>11 listopada 2026 otworzyliśmy z komputera w USA, bez VPN, stronę „Faktów” w Playerze. Przez chwilę było widać opis programu i listę wydań. Potem serwis sam przeniósł nas pod adres player.pl/international. Na ciemnym ekranie zostało logo i jedno zdanie:</p>
<blockquote>Ups... Player jest niedostępny w Twojej lokalizacji</blockquote>
<p>W prawym dolnym rogu Player wypisuje adres IP i skrót kraju, który rozpoznał. U nas było to „US”. Nie ma przycisku, logowania ani menu.</p>

<h2>To inna blokada niż w TVP VOD</h2>
<p>TVP VOD blokuje pojedynczy materiał i resztę serwisu zostawia otwartą. Player w USA zamknął wszystko: stronę główną, listy odcinków i logowanie. Nie da się więc nawet sprawdzić, czy inny odcinek działa.</p>

<h2>Inne komunikaty Playera o lokalizacji</h2>
<p>W tekstach serwisu są jeszcze komunikaty dla widzów, których Player wpuszcza, ale ogranicza. Nie widzieliśmy ich w teście, bo nasz adres był spoza Unii:</p>
<div class="scrollx keep"><table class="mini3"><thead><tr><th>Komunikat</th><th>Co oznacza</th></tr></thead><tbody>
<tr><td>„Materiał niedostępny w Twojej lokalizacji. Przykro nam, materiały w player można odtwarzać tylko na terenie Unii Europejskiej.”</td><td>Odtwarzanie działa tylko w krajach Unii.</td></tr>
<tr><td>„Ze względu na ograniczenia licencyjne nie możesz oglądać wybranego materiału wideo w Twojej obecnej lokalizacji.”</td><td>Ten jeden materiał ma licencję tylko na Polskę. Inne mogą działać.</td></tr>
<tr><td>„Nie możemy wyświetlić tego materiału. Aby odtwarzać wybrany materiał w Twojej lokalizacji, aktywuj dostęp do swojego pakietu w całej Unii Europejskiej.”</td><td>Masz płatny pakiet kupiony w Polsce, ale nie potwierdziłeś jeszcze dostępu w Unii. Zrobisz to na swoim koncie.</td></tr>
</tbody></table></div>

<h2>Co możesz zrobić</h2>
<h3>1. Player International</h3>
<p>To oficjalny pakiet dla widzów za granicą: 50 zł za 30 dni, z siedmiodniowym okresem próbnym. Zawiera bibliotekę Playera bez reklam oraz kanały ITVN, ITVN Extra i TVN24. Player sprzedaje go w wybranych krajach, a zawartość różni się od pakietów w Polsce. Źródło: __PLAYERINT__, sprawdzone 11.11.2026.</p>
<h3>2. Masz pakiet kupiony w Polsce i jesteś w Unii</h3>
<p>Włącz na koncie dostęp w całej Unii Europejskiej. Dotyczy to osób mieszkających w Polsce, które wyjechały czasowo. Darmowych odcinków ta droga nie obejmuje.</p>
<h3>3. VPN z serwerem w Polsce</h3>
<p>Z polskim adresem IP Player otwiera się jak w kraju, razem z odcinkami oznaczonymi „BEZ OPŁAT”. Codziennie sprawdzamy, czy darmowe wydanie „Faktów” gra przez VPN z serwerem w Polsce. Wynik i szczegóły są w poradniku <a href="/player-za-granica">Player za granicą</a>.</p>

<h2>Wskazówka: sprawdź, jaki kraj widzi Player</h2>
<p>Skrót kraju w rogu ekranu z komunikatem jest przydatny. Jeśli masz włączony VPN i dalej widzisz ten ekran, przeczytaj skrót. „NL” albo „DE” znaczy, że aplikacja VPN połączyła Cię z Holandią albo Niemcami, a nie z Polską. Zmień serwer na polski i odśwież stronę.</p>
""".replace("__PLAYERINT__", SRC_PLAYERINT), "prosec", brief([("Rodzaj błędu", "Blokada całego serwisu"), ("Kiedy się pojawia", "Od razu po wejściu"), ("Nasz test", "USA, bez VPN, 11.11.2026"), ("Oficjalna opcja", "Player International")],
                     [("/player-za-granica", "Poradnik: Player za granicą"), ("/tvp-vod-material-niedostepny-w-twoim-kraju", "Podobny komunikat w TVP VOD"), ("/porownanie-vpn", "Ranking VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + faq([("Czy Player działa w Wielkiej Brytanii?", "Nie sprawdzaliśmy tego z adresu w Wielkiej Brytanii. Komunikaty serwisu mówią o Unii Europejskiej, a Wielka Brytania do niej nie należy."),
           ("Czy aplikacja na telefon albo telewizor ominie ten komunikat?", "Nie. Aplikacja łączy się przez ten sam adres IP co przeglądarka."),
           ("Dlaczego strona najpierw się ładuje, a potem znika?", "Player sprawdza lokalizację po załadowaniu strony. W naszym teście opis programu było widać przez chwilę, zanim serwis przeniósł nas na ekran z komunikatem."),
           ("Czy Player International to to samo co Player w Polsce?", "Nie. To osobny pakiet z własną zawartością. Część programów z polskiej oferty może w nim nie być.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/player-za-granica", "Player"), ("/player-niedostepny-w-twojej-lokalizacji", "Player niedostępny w Twojej lokalizacji")])

PAGES["/tvp-sport-material-niedostepny"] = ("TVP Sport: „materiał jest niedostępny w kraju, z którego się łączysz” | Polski Streaming",
    "TVP Sport za granicą pokazuje „Przepraszamy. Z uwagi na ograniczenia licencyjne materiał jest niedostępny”. Zrzut ekranu z testu, przyczyna i wyjścia przed meczem.",
    band('<a href="/">Polska telewizja za granicą</a> / <a href="/tvp-sport-za-granica">TVP Sport</a> / Komunikat', "TVP Sport: „materiał jest niedostępny w kraju, z którego się łączysz”",
         "Tak TVP Sport informuje o blokadzie regionalnej. Zobacz, jak wygląda komunikat i co zrobić przed transmisją.",
         errwhen(), figure=frame("/img/blok-tvpsport.webp", "sport.tvp.pl", "Zrzut ekranu z naszego testu bez VPN, 11.11.2026, adres IP z USA."))
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> Odtwarzacz TVP Sport rozpoznał adres IP spoza Polski i nie puścił wideo. Artykuły, wyniki i program transmisji dalej działają. Wideo ruszy z polskim adresem IP. Przed ważnym meczem sprawdź połączenie wcześniej na dowolnym materiale.</p>

<h2>Jak wygląda komunikat</h2>
<p>11 listopada 2026 otworzyliśmy z komputera w USA, bez VPN, najnowszy materiał z działu „Wideo”: krótką rozmowę o koszykarskiej reprezentacji Polek. Artykuł załadował się w całości. W oknie odtwarzacza, na czarnym tle, pojawił się biały napis:</p>
<blockquote>Przepraszamy. Z uwagi na ograniczenia licencyjne materiał jest niedostępny w kraju z którego się łączysz.</blockquote>
<p>Przycisk odtwarzania jest widoczny, ale po kliknięciu nic się nie dzieje. Licznik pokazuje długość materiału, u nas 25 sekund.</p>
<p>To ważna obserwacja: zablokowany był krótki, własny materiał TVP, a nie mecz na żywo. W USA blokada objęła więc także dział „Wideo”.</p>

<h2>Trzy wersje tego komunikatu</h2>
<p>Odtwarzacz TVP ma w swoich tekstach trzy warianty. Pierwszy widzieliśmy w teście, dwa kolejne znamy z kodu odtwarzacza:</p>
<div class="scrollx keep"><table class="mini3"><thead><tr><th>Komunikat</th><th>Gdzie się pojawia</th></tr></thead><tbody>
<tr><td>„Przepraszamy. Z uwagi na ograniczenia licencyjne materiał jest niedostępny w kraju z którego się łączysz.”</td><td>W oknie odtwarzacza przy materiale wideo. Wariant z naszego testu.</td></tr>
<tr><td>„Materiał niedostępny” albo „Geoblokada” w tytule okna</td><td>Ten sam powód, inny nagłówek.</td></tr>
<tr><td>„Ze względów licencyjnych materiał niedostępny poza granicami Polski.”</td><td>Plansza zamiast transmisji na żywo.</td></tr>
</tbody></table></div>

<h2>Dlaczego sport jest blokowany częściej</h2>
<p>Prawa do meczów i zawodów sprzedaje się osobno dla każdego kraju. TVP kupuje je na Polskę, a w Niemczech albo w USA to samo wydarzenie ma innego nadawcę. TVP musi więc zamknąć transmisję dla widzów za granicą.</p>

<h2>Co możesz zrobić</h2>
<h3>1. Sprawdź nadawcę w kraju, w którym mieszkasz</h3>
<p>Duże wydarzenia są zwykle w lokalnej telewizji, czasem bezpłatnie. Skoki narciarskie w sezonie 2026/27 pokazują w Niemczech ARD, ZDF i Eurosport. Komentarz jest wtedy w języku danego kraju. Więcej w poradniku <a href="/polska-telewizja-w-niemczech">Polska telewizja w Niemczech</a>.</p>
<h3>2. VPN z serwerem w Polsce</h3>
<p>Z polskim adresem IP odtwarzacz działa jak w kraju, z polskim komentarzem. W naszych codziennych testach materiały z działu „Wideo” grały przez VPN z serwerem w Polsce. Transmisji na żywo jeszcze nie testujemy.</p>
<h3>3. Przed meczem zrób próbę</h3>
<ul>
  <li>Połącz VPN kilkanaście minut przed startem i włącz dowolny materiał z działu „Wideo”.</li>
  <li>Jeśli widzisz komunikat, zmień serwer na inny polski i odśwież stronę.</li>
  <li>Przed każdym wideo są reklamy. W naszych testach trwały od 46 do 55 sekund, więc nie czekaj do pierwszego gwizdka.</li>
</ul>
""", "prosec", brief([("Rodzaj błędu", "Blokada regionalna"), ("Gdzie się pojawia", "W oknie odtwarzacza"), ("Nasz test", "USA, bez VPN, 11.11.2026"), ("Materiał w teście", "Wideo, 25 sekund")],
                     [("/tvp-sport-za-granica", "Poradnik: TVP Sport za granicą"), ("/tvp-vod-material-niedostepny-w-twoim-kraju", "Komunikat w TVP VOD"), ("/porownanie-vpn", "Ranking VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + faq([("Czy TVP Sport działa za granicą bez VPN?", "Strona, artykuły i wyniki tak. W naszym teście z USA wideo było zablokowane. Z krajów Unii jeszcze nie sprawdzaliśmy."),
           ("Czy aplikacja TVP Sport zachowuje się inaczej niż strona?", "Testujemy stronę w przeglądarce. Aplikacja korzysta z tego samego adresu IP, więc blokada regionalna działa w niej tak samo."),
           ("Czy transmisja zadziała, jeśli wideo działa?", "Nie mamy na to wyniku testu. Transmisje mają osobne licencje, dlatego zrób próbę przed meczem i miej drugi polski serwer w zapasie.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/tvp-sport-za-granica", "TVP Sport"), ("/tvp-sport-material-niedostepny", "Materiał niedostępny")])

PAGES["/polska-telewizja-w-uk"] = ("Polska telewizja w UK: co działa po brexicie | Polski Streaming",
    "Polska telewizja w Wielkiej Brytanii: brak polskich kanałów w Sky i Virgin, druga antena na Hot Bird, Player International, TV Licence i VPN.",
    band('<a href="/">Polska telewizja za granicą</a> / Wielka Brytania', "Polska telewizja w UK",
         "Po brexicie polskie serwisy działają w Wielkiej Brytanii inaczej niż w Unii. Sprawdziliśmy operatorów, satelitę, oficjalne pakiety i zasady TV Licence.",
         f'<div class="when mono">{BYLINE}<span>Dane sprawdzone: <b>11.11.2026</b></span></div>', image="livingroom")
    + prose("""
<p class="answer"><b>Krótka odpowiedź.</b> W Wielkiej Brytanii jest trudniej niż w krajach Unii. Na listach kanałów Sky i Virgin Media nie znaleźliśmy żadnego polskiego kanału. Po brexicie nie działa też unijna zasada, która pozwala zabrać polski abonament za granicę. Zostają trzy drogi: druga antena satelitarna na darmowe kanały, pakiet Player International albo VPN z serwerem w Polsce.</p>

<p>W Anglii i Walii mieszka 743 000 osób urodzonych w Polsce (spis powszechny 2021, <a href="https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/internationalmigration/bulletins/internationalmigrationenglandandwales/census2021" target="_blank" rel="nofollow noopener">ONS</a>). W Szkocji jest to 75 400 osób (spis 2022, <a href="https://www.scotlandscensus.gov.uk/2022-reports/scotland-s-census-2022-demography-and-migration/" target="_blank" rel="nofollow noopener">Scotland's Census</a>).</p>

<h2>Co zmienił brexit</h2>
<p>W Unii Europejskiej działa rozporządzenie 2017/1128. Dzięki niemu płatny pakiet kupiony w Polsce działa podczas pobytu w innym kraju Unii. Wielka Brytania tę zasadę uchyliła. Rząd pisze wprost: „The EU Portability Regulation no longer applies to UK-EEA travel” (<a href="https://www.gov.uk/guidance/cross-border-portability-of-online-content-services-after-the-transition-period" target="_blank" rel="nofollow noopener">gov.uk</a>).</p>
<p>W praktyce: polski pakiet Polsat Box Go, Canal+ Online albo TVP VOD nie musi działać w UK, nawet jeśli działa w Niemczech czy w Irlandii. O dostępie decyduje sam serwis.</p>

<h2>Porównanie sposobów</h2>
<div class="scrollx keep"><table class="mini3"><thead><tr><th>Sposób</th><th>Co dostajesz</th><th>Koszt</th></tr></thead><tbody>
<tr><td>Sky, Virgin Media</td><td>Brak polskich kanałów na listach z czerwca 2026</td><td>Nie dotyczy</td></tr>
<tr><td>Satelita Hot Bird 13°E</td><td>TVP Polonia, Polonia 1, Tele 5 i inne kanały niekodowane</td><td>Jednorazowo antena i montaż</td></tr>
<tr><td>Player International</td><td>Biblioteka Playera bez reklam, ITVN, ITVN Extra, TVN24</td><td>50 zł za 30 dni</td></tr>
<tr><td>VPN z serwerem w Polsce</td><td>Polska wersja serwisów: TVP VOD, Player, TVP Sport</td><td>od 6,29 zł za miesiąc</td></tr>
</tbody></table></div>

<h2>1. Sky i Virgin Media: polskich kanałów brak</h2>
<p>Sprawdziliśmy listy kanałów prowadzone przez serwis RXTV: <a href="https://rxtvinfo.com/sky-satellite-channel-list-uk/" target="_blank" rel="nofollow noopener">Sky z satelity</a> (stan na 26.06.2026), Sky Glass i Sky Stream (08.06.2026) oraz <a href="https://rxtvinfo.com/virgin-media-channel-list-uk/" target="_blank" rel="nofollow noopener">Virgin Media</a> (28.05.2026). Na żadnej nie ma TVP Polonia, ITVN ani innego polskiego kanału.</p>
<p>Virgin Media miał kiedyś pakiet „Polish Impreza” z TVP Polonia i ITVN za 8 funtów miesięcznie. Ruszył w 2017 roku. Nie znaleźliśmy potwierdzenia, że jest dziś w sprzedaży, więc zapytaj operatora, zanim podpiszesz umowę.</p>

<h2>2. Satelita: potrzebna druga antena</h2>
<p>Polskie kanały niekodowane nadają z satelity Hot Bird (13°E). Antena Sky albo Freesat patrzy na inną pozycję, 28,2°E, więc ich nie złapie. Potrzebujesz osobnej czaszy skierowanej na 13°E.</p>
<ul>
  <li><b>Rozmiar czaszy:</b> instalatorzy podają co najmniej 70 cm, a najlepiej około 80 cm. W Szkocji i na północy Anglii potrzeba większej (<a href="https://smartaerials.co.uk/blog/how-to-get-polish-satellite-tv-polsat-in-uk" target="_blank" rel="nofollow noopener">Smart Aerials, 2022</a>).</li>
  <li><b>Dla porównania:</b> do Sky wystarcza 45 cm na południu i 60 cm na północy.</li>
  <li><b>Co odbierzesz za darmo:</b> TVP Polonia, TVP World, Polonia 1, Tele 5, TVS, Kanał Zero TV i kanały muzyczne. TVP1, TVP2, Polsat i TVN są zakodowane.</li>
</ul>
<p>W wynajmowanym mieszkaniu zapytaj właściciela o zgodę na montaż anteny.</p>

<h2>3. Polskie serwisy w UK</h2>
<h3>Player</h3>
<p>W tekstach Playera jest komunikat: „materiały w player można odtwarzać tylko na terenie Unii Europejskiej”. Wielka Brytania do Unii nie należy. Z adresu w USA zobaczyliśmy w teście ekran <a href="/player-niedostepny-w-twojej-lokalizacji">„Player jest niedostępny w Twojej lokalizacji”</a>. Z adresu w UK jeszcze nie sprawdzaliśmy.</p>
<p>Oficjalną drogą jest Player International: 50 zł za 30 dni, z siedmiodniowym okresem próbnym. Zawiera bibliotekę Playera bez reklam oraz kanały ITVN, ITVN Extra i TVN24. Player sprzedaje go w wybranych krajach. Pakiet TVN dla zagranicy był najpierw sprzedawany właśnie w Wielkiej Brytanii (Telepolis, 2019). Źródło: """ + SRC_PLAYERINT + """.</p>
<h3>TVP VOD i TVP Sport</h3>
<p>Oba serwisy blokują pojedyncze materiały według adresu IP. W teście z USA TVP VOD pokazał <a href="/tvp-vod-material-niedostepny-w-twoim-kraju">„materiał jest niedostępny w Twoim kraju”</a>, a TVP Sport zablokował nawet krótkie wideo. Z adresu w UK jeszcze nie sprawdzaliśmy, więc otwórz najpierw swój program bez VPN.</p>
<h3>Polsat Box Go</h3>
<p>Polsat pisze w pomocy, że serwis „jest dostępny za granicą w wybranych krajach” i że ma osobne pakiety dla widzów z zagranicy. Listy krajów ani ceny tam nie ma. Więcej w poradniku <a href="/polsat-box-go-za-granica">Polsat Box Go za granicą</a>.</p>

<h2>4. VPN z serwerem w Polsce</h2>
<p>VPN daje polski adres IP, więc serwis pokazuje Ci krajową wersję. W UK to jedyna droga do darmowych odcinków Playera i do pełnej oferty TVP VOD. Używanie VPN jest w Wielkiej Brytanii legalne. Regulamin serwisu może jednak zabraniać omijania blokad regionalnych, a serwisy blokują część adresów VPN.</p>
<p>Codziennie sprawdzamy botem trzy polskie serwisy przez VPN z serwerem w Polsce. Dzisiejsze wyniki znajdziesz na stronie <a href="/wyniki-testow">Wyniki testów</a>.</p>

<h2>TV Licence obowiązuje także przy polskiej telewizji na żywo</h2>
<p>To często pomijana sprawa. TV Licensing pisze, że licencja jest potrzebna do oglądania telewizji na żywo w każdej usłudze, „no matter where it is broadcast or distributed from”, także przy programach z satelity i transmisjach internetowych spoza UK (<a href="https://www.tvlicensing.co.uk/faqs/FAQ16" target="_blank" rel="nofollow noopener">TV Licensing, wersja z sierpnia 2025</a>).</p>
<ul>
  <li><b>Licencja jest potrzebna:</b> gdy oglądasz kanał na żywo, na przykład TVP Polonia z satelity albo transmisję meczu w internecie.</li>
  <li><b>Opłata:</b> 180 funtów za rok (<a href="https://www.gov.uk/find-licences/tv-licence" target="_blank" rel="nofollow noopener">gov.uk</a>).</li>
  <li><b>Odcinki na żądanie</b> z polskich serwisów to inna sytuacja. Sprawdź zasady na stronie TV Licensing.</li>
</ul>

<h2>Sport: inna godzina i inni nadawcy</h2>
<p>W UK jest godzina wcześniej niż w Polsce. Mecz o 20:45 czasu polskiego zaczyna się o 19:45 czasu brytyjskiego.</p>
<ul>
  <li><b>Skoki narciarskie:</b> sporty zimowe przeszły w UK z Eurosportu do TNT Sports w lutym 2025 roku. TNT Sports jest płatny, a komentarz jest po angielsku.</li>
  <li><b>Liga Narodów 2026/27:</b> mecze Anglii pokazuje ITV, a Szkocji, Walii i Irlandii Północnej BBC. Wybrane pozostałe mecze są w Prime Video w systemie płatności za mecz.</li>
  <li><b>Polski komentarz:</b> jest w TVP Sport. Jak wygląda blokada i jak zrobić próbę przed meczem, opisujemy na stronie <a href="/tvp-sport-material-niedostepny">TVP Sport: materiał niedostępny</a>.</li>
</ul>
""",
    "prosec", brief([("Polskie kanały w Sky i Virgin", "Nie znaleźliśmy"), ("Za darmo", "Hot Bird 13°E, druga antena"), ("Zasada z Unii o abonamencie", "Nie działa w UK"), ("TV Licence", "180 funtów za rok")],
                     [("/polska-telewizja-w-niemczech", "Polska telewizja w Niemczech"), ("/player-za-granica", "Player za granicą"), ("/porownanie-vpn", "Ranking VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + faq([("Czy Sky ma polskie kanały?", "Na listach kanałów Sky z czerwca 2026, prowadzonych przez serwis RXTV, nie znaleźliśmy żadnego polskiego kanału."),
           ("Czy antena Sky odbierze TVP Polonia?", "Nie. Antena Sky patrzy na pozycję 28,2°E, a polskie kanały niekodowane są na Hot Bird 13°E. Potrzebna jest osobna czasza, najlepiej około 80 cm."),
           ("Czy mój polski abonament Polsat Box Go albo Canal+ zadziała w Anglii?", "Nie ma takiej gwarancji. Unijna zasada o przenoszeniu abonamentu nie obowiązuje w Wielkiej Brytanii od 2021 roku. Zapytaj swój serwis przed wyjazdem."),
           ("Czy muszę płacić TV Licence, jeśli oglądam tylko polską telewizję?", "Tak, jeśli oglądasz kanały na żywo. TV Licensing pisze, że licencja dotyczy telewizji na żywo niezależnie od kraju nadawania."),
           ("Czy VPN jest legalny w UK?", "Tak. Regulamin serwisu streamingowego może jednak zabraniać omijania blokad regionalnych.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/polska-telewizja-w-uk", "Polska telewizja w UK")])

PAGES["/polsat-box-go-za-granica"] = ("Jak oglądać Polsat Box Go za granicą | Polski Streaming",
    "Polsat Box Go za granicą: co działa w UE, pakiet Polonia i dlaczego jeszcze nie testujemy tego serwisu.",
    band('<a href="/">Polska telewizja za granicą</a> / Polsat Box Go', "Jak oglądać Polsat Box Go za granicą",
         "Polsat Box Go wymaga konta, a większość treści jest płatna. Tego serwisu jeszcze nie testujemy, więc na tej stronie są tylko sprawdzone fakty i źródła.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>{UPDATED}</b></span></div>', image="livingroom")
    + prose(f"""
<p class="note"><b>Nie testujemy jeszcze Polsat Box Go.</b> Do testu potrzebny jest płatny pakiet. Nie publikujemy wyników, których sami nie zmierzyliśmy. Gdy zaczniemy testy, wynik pojawi się na tej stronie.</p>

<h2>Co sprawdziliśmy sami ({CHECKED})</h2>
<ul>
  <li>Adres polsatgo.pl przekierowuje teraz do polsatboxgo.pl. Osobnego darmowego serwisu Polsat Go już tam nie ma.</li>
  <li>Próba odtworzenia serialu „Świat według Kiepskich” bez konta kończy się przekierowaniem na stronę logowania.</li>
</ul>

<h2>Sposoby</h2>
<h3>1. Wyjazd w Unii Europejskiej</h3>
<p>Płatny pakiet działa podczas czasowego pobytu w innym kraju UE na mocy rozporządzenia 2017/1128. Kluczowe jest słowo „czasowo”: chodzi o wyjazd, a nie o stałe mieszkanie za granicą. Zasada nie obejmuje Wielkiej Brytanii ani USA.</p>
<h3>2. Pakiet dla widzów za granicą</h3>
<p>Według serwisów <a href="https://bezprawnik.pl/jak-ogladac-tv-za-granica/" target="_blank" rel="noopener">Bezprawnik</a> i <a href="https://android.com.pl/sponsorowany/436490-polsat-box-go-co-wybrac-roznice-grupa-plus/" target="_blank" rel="noopener">Android.com.pl</a> Polsat Box Go ma pakiet „Polonia” dla osób przebywających poza Polską. Nie potwierdziliśmy tego w oficjalnym cenniku. Aktualną ofertę sprawdź na <a href="https://polsatboxgo.pl/pakiety" target="_blank" rel="noopener">polsatboxgo.pl/pakiety</a>.</p>
<h3>3. VPN z serwerem w Polsce</h3>
<!--flow:polsat-->
<p>Inne serwisy opisują VPN jako sposób na Polsat Box Go. My tego nie sprawdziliśmy, więc nie podajemy, który VPN działa. Wyniki mamy dla <a href="/tvp-vod-za-granica">TVP VOD</a> i <a href="/player-za-granica">Playera</a>.</p>
<p><a class="btn" href="/porownanie-vpn">Zobacz ranking VPN z serwerem w Polsce</a></p>
""", "prosec", brief([("Konto", "Wymagane"), ("Darmowe treści bez konta", "Nie znaleźliśmy"), ("W Unii Europejskiej", "Działa na czasowym wyjeździe"), ("Nasz test", "Jeszcze nie testujemy")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/player-za-granica", "Player za granicą"), ("/porownanie-vpn", "Porównanie VPN")])),
    "article", [("/", "Polska telewizja za granicą"), ("/polsat-box-go-za-granica", "Polsat Box Go")])

PAGES["/promocje-vpn"] = ("Promocje VPN na Black Friday 2026: ceny sprawdzone " + PRICED + " | Polski Streaming",
    "Promocje VPN na Black Friday 2026: NordVPN, Surfshark, Proton VPN, CyberGhost i ExpressVPN. Cena w promocji, cena bez promocji, ile płacisz z góry i ile po pierwszym okresie.",
    band('<a href="/">Polska telewizja za granicą</a> / Promocje VPN', "Promocje VPN: Black Friday 2026",
         "Pięć VPN z serwerem w Polsce i ich oferty na Black Friday. Każdą cenę odczytaliśmy sami z polskiej strony dostawcy. Pokazujemy też to, czego reklama nie mówi: ile płacisz z góry i ile kosztuje odnowienie.",
         f'<div class="when mono">{BYLINE}<span>Ceny odczytane: <b>{PRICED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>')
    + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Oferty Black Friday, stan na {PRICED}</h2><p>Kolejność jak w naszym <a href="/porownanie-vpn">rankingu punktowym</a>, nie według wielkości rabatu. Dostawcy nie podają daty końca promocji, więc oferta może się zmienić z dnia na dzień.</p></div>
  {DISCLOSE}
  <div class="deals">{deals_page()}</div>
</div></section>"""
    + prose(f"""
<h2>Jak czytać te promocje</h2>
<ul>
  <li><b>Rabat liczy dostawca.</b> Zwykle porównuje cenę długiego planu z ceną planu na jeden miesiąc. Dlatego rabaty są tak duże.</li>
  <li><b>Płacisz z góry za cały okres.</b> Cena „za miesiąc” to suma podzielona przez liczbę miesięcy. Przy NordVPN to 253,53 zł od razu, a nie 9,39 zł co miesiąc.</li>
  <li><b>Po pierwszym okresie jest drożej.</b> Proton VPN odnawia się za 209,88 zł co 12 miesięcy, ExpressVPN za 79,95 € za rok. NordVPN i Surfshark pokazują cenę odnowienia dopiero przy zamówieniu.</li>
  <li><b>Masz czas na zwrot.</b> Każdy z pięciu dostawców daje co najmniej 30 dni na zwrot pieniędzy w długim planie. To wystarczy, żeby sprawdzić VPN ze swoim serwisem.</li>
</ul>
<h2>Który VPN z promocji działa z polską telewizją</h2>
<p>Promocja nic nie da, jeśli film nie ruszy. Codziennie rano sprawdzamy NordVPN i Proton VPN Plus z TVP VOD, Playerem i TVP Sport. Wynik z {LAST[:10]}:</p>
<div data-last>{last_rows_html()}</div>
<p>Surfsharka, CyberGhost i ExpressVPN jeszcze nie testujemy. Ich ceny są sprawdzone, ale działania z polskimi serwisami nie potwierdziliśmy. <a href="/wyniki-testow">Wyniki dzień po dniu</a>.</p>
<h2>Skąd mamy ceny</h2>
<p>{PRICED} otworzyliśmy polskie strony cenników wszystkich pięciu dostawców i zapisaliśmy to, co pokazują: cenę za miesiąc, sumę do zapłaty i rabat. Nie przepisujemy cen z innych serwisów. Ceny w euro przeliczamy po kursie {EUR}. Gdy cena się zmieni, poprawiamy ją tutaj i w <a href="/porownanie-vpn">rankingu</a>.</p>
""", "prosec")
    + faq([("Kiedy kończą się promocje VPN na Black Friday 2026?", f"Black Friday wypada 27 listopada 2026. Żaden z pięciu dostawców nie podaje na stronie cennika daty końca promocji. Ceny na tej stronie odczytaliśmy {PRICED}."),
           ("Czy cena z promocji zostaje na zawsze?", "Nie. Cena z promocji dotyczy pierwszego okresu, zwykle 24 do 28 miesięcy. Potem plan odnawia się po wyższej cenie. Odnowienie można wyłączyć na koncie u dostawcy."),
           ("Czy mogę oddać VPN kupiony w promocji?", "Tak. W długich planach NordVPN, Surfshark, Proton VPN i ExpressVPN dają 30 dni na zwrot pieniędzy, a CyberGhost 45 dni. ExpressVPN daje zwrot tylko nowym klientom."),
           ("Który VPN z promocji jest najtańszy?", f"Na {PRICED} najniższą cenę za miesiąc ma Proton VPN: 6,29 zł w planie na 2 lata, razem 150,96 zł z góry."),
           ("Jak zarabia ta strona?", "Część linków na stronie to linki partnerskie. Dziś partnerami są __PARTNERS__: gdy kupisz przez nasz link, dostajemy prowizję, a Ty płacisz tyle samo. Prowizja nie zmienia kolejności ani cen na tej stronie.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/promocje-vpn", "Promocje VPN")])

PAGES["/porownanie-vpn"] = ("Ranking VPN do polskiej telewizji 2026 | Polski Streaming",
    "Ranking pięciu VPN z serwerem w Polsce: ceny w złotówkach, zwrot pieniędzy, liczba urządzeń, zalety i wady. Jawne zasady punktacji.",
    band('<a href="/">Polska telewizja za granicą</a> / Porównanie VPN', "Ranking VPN do polskiej telewizji",
         "Pięciu dostawców, te same pytania do każdego: ile kosztuje, czy ma serwer w Polsce i ile daje czasu na zwrot. Dwóch z nich testujemy codziennie z TVP VOD, Playerem i TVP Sport.",
         f'<div class="when mono">{BYLINE}<span>Ceny sprawdzone: <b>{PRICED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>', image="shield")
    + rank_top()
    + bf_box()
    + QUIZ
    + f"""<section class="guides"><div class="wrap">
  <div class="shead"><h2>Każdy VPN z rankingu w szczegółach</h2><p>Zalety, wady, pełne warunki ceny i źródła danych. Kolejność jak w rankingu: serwery w Polsce, cena, urządzenia, zwrot, aplikacje i waluta. <a href="#ranking">Zasady punktacji</a> są niżej.</p></div>
  <div class="pblist">{provblocks()}</div>
  <p class="after">Ceny odczytaliśmy ze stron dostawców {PRICED}. To ceny promocyjne za pierwszy okres i mogą się zmienić. Po pierwszym okresie plan odnawia się zwykle drożej.</p>
</div></section>"""
    + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Tabela porównawcza</h2><p>Dane ze stron dostawców, sprawdzone {CHECKED}.</p></div>
  {facts_table()}
  <p class="monly muted">Na telefonie te same dane są wyżej, przy każdym dostawcy.</p>
</div></section>"""
    + DEVICES
    + prose("""
<h2>Jak wybrać VPN do polskiej telewizji</h2>
<ul>
  <li><b>Serwer w Polsce.</b> Bez niego VPN nie da Ci polskiego adresu IP. To warunek konieczny i wszyscy z zestawienia go spełniają.</li>
  <li><b>Wynik testu, nie reklama.</b> Każdy dostawca pisze, że „działa ze streamingiem”. Liczy się to, czy film naprawdę gra. Nasze własne pomiary są na stronie <a href="/wyniki-testow">Wyniki testów</a>.</li>
  <li><b>Cena po promocji.</b> Niska cena dotyczy pierwszego okresu. Sprawdź, ile kosztuje odnowienie, zanim kupisz plan na dwa lata.</li>
  <li><b>Zwrot pieniędzy.</b> Kup, sprawdź ze swoim serwisem i poproś o zwrot, jeśli nie działa. Przeczytaj warunki zwrotu przed zakupem.</li>
  <li><b>Aplikacja na telewizor.</b> Jeśli oglądasz na TV, sprawdź, czy dostawca ma aplikację na Twoją platformę.</li>
</ul>
<h2 id="ranking">Jak liczymy ranking</h2>
<p>Ocena w skali 10, którą widzisz przy każdym VPN, to te same punkty podzielone przez 19 i pomnożone przez 10. Nie jest to ocena użytkowników.</p>
<p>Każdy dostawca dostaje punkty w sześciu kategoriach. Liczymy tylko fakty, które każdy może sprawdzić na stronie dostawcy. Prowizja partnerska nie daje punktów.</p>
<ul>
  <li><b>Serwery w Polsce:</b> 6 punktów za podaną liczbę co najmniej 50 serwerów, 2 punkty za jedną lokalizację. Ta kategoria liczy się podwójnie. Serwisy blokują pojedyncze adresy VPN, więc przy większej liczbie serwerów łatwiej przełączyć się na inny.</li>
  <li><b>Cena za miesiąc w najtańszym planie:</b> 3 punkty poniżej 9 zł, 2 punkty do 10,50 zł, 1 punkt powyżej. Euro przeliczamy po kursie """ + EUR + """.</li>
  <li><b>Urządzenia jednocześnie:</b> 3 punkty od 14 w górę, 2 punkty za 10, 1 punkt poniżej 10.</li>
  <li><b>Zwrot pieniędzy:</b> 3 punkty od 45 dni, 2 punkty za 30 dni.</li>
  <li><b>Aplikacje na telewizor:</b> 3 punkty za Android TV, Apple TV i Fire TV.</li>
  <li><b>Płatność w złotówkach:</b> 1 punkt.</li>
</ul>
""" + points_table() + """
<p>Przy remisie wyżej jest dostawca z większą liczbą serwerów w Polsce, a potem tańszy.</p>
<p class="note"><b>To ranking na podstawie danych producentów, a nie testów.</b> Własny codzienny test mamy dziś dla """ + str(len(tested_companies())) + """ z 5 dostawców: """ + " i ".join(tested_companies()) + """. Wyniki testu są na stronie <a href="/wyniki-testow">Wyniki testów</a>. Nie wliczamy ich do punktów, dopóki nie przetestujemy wszystkich pięciu dostawców.</p>
""", "prosec", brief([("Testujemy dziś", " i ".join(tested_companies())), ("Serwisy w teście", "TVP VOD, Player, TVP Sport"), ("Ceny", "Ze stron dostawców, z datą")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/player-za-granica", "Player za granicą"), ("/darmowy-vpn-polska-telewizja", "Darmowy VPN")])),
    "article", [("/", "Polska telewizja za granicą"), ("/porownanie-vpn", "Porównanie VPN")])

PAGES["/jak-testujemy"] = ("Jak testujemy VPN z polskimi serwisami | Polski Streaming",
    "Metodologia: bot łączy się z polskim serwerem VPN, sprawdza adres IP, włącza film na 60 sekund i zapisuje zrzut ekranu.",
    band('<a href="/">Polska telewizja za granicą</a> / Jak testujemy', "Jak testujemy",
         "Ten sam test każdego ranka. Wyniki publikujemy także wtedy, gdy są złe dla dostawcy.",
         WHEN, image="europe")
    + """<section class="method"><div class="wrap">
  <div class="shead"><h2>Przebieg testu</h2><p>Test jest automatyczny. Nikt nie poprawia wyników ręcznie.</p></div>
  <div class="tl">
    <div><time>Krok 1</time><h3>Połączenie z VPN</h3><p>Polski serwer dostawcy, protokół WireGuard.</p></div>
    <div><time>Krok 2</time><h3>Kontrola adresu IP</h3><p>Adres musi być polski. Inaczej test się nie odbywa.</p></div>
    <div><time>Krok 3</time><h3>Pomiar prędkości</h3><p>Trzy pobrania po 20 MB, wynik to średnia.</p></div>
    <div><time>Krok 4</time><h3>Otwarcie serwisu</h3><p>Zwykła przeglądarka Chrome, bez logowania.</p></div>
    <div><time>Krok 5</time><h3>Reklamy</h3><p>Bot czeka do 5,5 minuty na koniec reklam.</p></div>
    <div><time>Krok 6</time><h3>Kontrola 60 sekund</h3><p>Film musi grać bez przerwy.</p></div>
    <div><time>Krok 7</time><h3>Zrzut ekranu</h3><p>Zapis obrazu po 20 sekundach filmu.</p></div>
  </div>
  <div class="mcols">
    <div><h3>Co oznaczają wyniki</h3><ul id="cats">""" + "".join(f"<li>{st(k)}<span>{d}</span></li>" for k, d in [
        ("ok", "Film grał 60 sekund bez przerwy w pierwszej próbie."), ("unstable", "Film zatrzymał się albo ruszył dopiero w drugiej próbie."),
        ("blocked", "Film nie ruszył w dwóch próbach. Powód może być po stronie VPN albo serwisu."), ("none", "Test się nie odbył. Nie liczymy tego jako blokady.")]) + """</ul></div>
    <div><h3>Ograniczenia</h3>
      <ul class="plain">
        <li>Wynik dotyczy serwera i przeglądarki użytych w teście.</li>
        <li>Prędkość mierzymy z jednego miejsca (podanego w tabeli), nie z każdego kraju.</li>
        <li>Po nieudanej próbie bot próbuje drugi raz. Dopiero dwie nieudane próby dają wynik „Nie działa”.</li>
        <li>Gdy odtwarzacz pokaże błąd albo komunikat o blokowaniu reklam, bot raz odświeża stronę, tak jak zrobiłby widz.</li>
        <li>Płatny plan, w którym film zagrał po odświeżeniu albo w drugiej próbie, ma wynik „Działa” z dopiskiem „po odświeżeniu”. Darmowy serwer w takim przypadku ma wynik „Niestabilny”. Szczegóły każdej próby są w danych testu.</li>
        <li>Nie widzimy przyczyny. „Nie działa” może wynikać z blokady, z obciążenia serwera VPN albo z awarii serwisu.</li>
      </ul>
    </div>
  </div>
</div></section>"""
    + prose("""
<h2>Czym testujemy</h2>
<ul>
  <li><b>Przeglądarka:</b> Chrome z obsługą DRM, okno 1440 × 900, język polski. Taka sama, jakiej używa zwykły widz.</li>
  <li><b>VPN:</b> konfiguracja WireGuard od dostawcy. Ruch przeglądarki idzie przez tunel, reszta systemu nie.</li>
  <li><b>Miejsce:</b> test uruchamia się na serwerze w chmurze. Kraj serwera podajemy przy wyniku prędkości.</li>
  <li><b>Pora:</b> raz dziennie rano czasu polskiego. Dokładną godzinę widać przy każdym wyniku.</li>
</ul>

<h2>Dlaczego używamy neutralnego serwera DNS</h2>
<p>Pierwsze testy z serwerem DNS dostawcy VPN kończyły się komunikatem o adblocku w TVP VOD i w Playerze. Serwer DNS dostawcy blokował domeny reklamowe, a oba serwisy nie puszczają filmu bez reklam. Po zmianie na neutralny DNS (1.1.1.1) film ruszył. Dlatego bot zawsze używa neutralnego DNS, a w poradnikach radzimy wyłączyć blokowanie reklam w aplikacji VPN.</p>

<h2>Co i kogo testujemy dziś</h2>
<p>Testujemy darmowe serwisy: TVP VOD, Player i TVP Sport. Płatnych serwisów jeszcze nie. Z dostawców VPN testujemy dziś: """ + tested_phrase() + """. Pozostałych dodamy, gdy będziemy mieć konta testowe. Do tego czasu ich wynik to „Nie przetestowano”.</p>
<p>Konto testowe NordVPN dostaliśmy bezpłatnie od NordVPN. Nie zmienia to sposobu testu ani wyniku: bot robi to samo dla każdego dostawcy, a złe dni zostają w historii. Konto testowe Proton VPN Plus też dostaliśmy bezpłatnie, od Proton. Osobno testujemy darmowy serwer Proton w Polsce.</p>

<h2 id="linki">Linki partnerskie</h2>
<p>Strona zarabia na linkach partnerskich: gdy kupisz VPN przez nasz link, dostajemy prowizję, a Ty płacisz tyle samo. <b>Dziś partnerami są __PARTNERS__.</b></p>
<p>Prowizja nie daje punktów w rankingu i nie zmienia wyników testu. Zasady punktacji są jawne i takie same dla każdego dostawcy.</p>

<h2>Skąd są dane w porównaniu</h2>
<p>Fakty o dostawcach (serwery, zwrot pieniędzy, liczba urządzeń) pochodzą z ich własnych stron. Przy każdej pozycji jest źródło i data sprawdzenia. Gdy czegoś nie potwierdzimy w źródle, nie podajemy tego.</p>

<h2>Czego nie robimy</h2>
<ul>
  <li>Nie publikujemy wyników, których bot nie zmierzył.</li>
  <li>Nie piszemy recenzji produktów, których nie używaliśmy.</li>
  <li>Nie usuwamy złych dni z historii.</li>
</ul>

<h2>Dziennik zmian</h2>
<ul>
  <li><b>19.11.2026:</b> nowe ceny Black Friday. CyberGhost (1,99 €) i ExpressVPN (2,39 €) dostały po jednym punkcie więcej za cenę i mają teraz równo po 12 punktów. Przy równej liczbie punktów wyżej jest tańszy plan. Kolejność w rankingu się nie zmieniła.</li>
  <li><b>15.11.2026:</b> jedno odświeżenie strony po błędzie odtwarzacza i dopisek „po odświeżeniu” dla płatnych planów.</li>
  <li><b>13.11.2026:</b> testujemy też płatny plan Proton VPN Plus (serwer PL#213, Warszawa). Darmowy serwer PL-FREE#1 testujemy dalej, osobno.</li>
  <li><b>10.11.2026:</b> pierwszy test (Proton VPN, TVP VOD, Player).</li>
  <li><b>10.11.2026:</b> dodany TVP Sport. Bot wybiera codziennie najnowszy materiał wideo z sport.tvp.pl.</li>
  <li><b>11.11.2026:</b> do codziennego testu doszedł NordVPN (plan płatny, serwer w Warszawie). Konto testowe dał nam NordVPN.</li>
  <li><b>11.11.2026:</b> w rankingu VPN liczba serwerów w Polsce liczy się podwójnie. Zasady są na stronie <a href="/porownanie-vpn#ranking">rankingu</a>.</li>
  <li><b>10.11.2026:</b> dodana druga próba po nieudanym teście i wynik „Niestabilny”.</li>
</ul>
""", "prosec", brief([("Częstotliwość", "Raz dziennie, rano"), ("Kryterium", "60 s filmu bez przerwy"), ("Dowód", "Zrzut ekranu z każdej próby"), ("Historia", "30 dni, także złe dni")],
                     [("/wyniki-testow", "Wyniki ostatniego testu"), ("/wyniki-testow#dowod", "Zrzuty ekranu"), ("/o-nas", "Kto prowadzi stronę")])),
    "article", [("/", "Polska telewizja za granicą"), ("/jak-testujemy", "Jak testujemy")])

PAGES["/o-nas"] = ("O nas | Polski Streaming",
    "Kto prowadzi Polski Streaming, po co powstała strona, jak powstają treści i z czego się utrzymuje.",
    band('<a href="/">Polska telewizja za granicą</a> / O nas', "O nas",
         "Polski Streaming to niezależna strona dla Polaków za granicą, którzy chcą oglądać polską telewizję.")
    + prose("""
<h2>Po co jest ta strona</h2>
<p>Strony o VPN zwykle piszą, że „wszystko działa”. My to sprawdzamy. Każdego ranka automatyczny test łączy się przez VPN z serwerem w Polsce, włącza film i zapisuje zrzut ekranu. Wynik publikujemy bez względu na to, czy jest dobry.</p>

<h2>Jak powstają treści</h2>
<ul>
  <li><b>Wyniki testów</b> pochodzą z naszego bota. Opis metody jest na stronie <a href="/jak-testujemy">Jak testujemy</a>.</li>
  <li><b>Fakty o dostawcach VPN</b> pochodzą z ich własnych stron, ze źródłem i datą.</li>
  <li><b>Poradniki</b> opisują to, co sami sprawdziliśmy w serwisach, oraz oficjalne opcje bez VPN.</li>
  <li>Przy pisaniu i programowaniu korzystamy z narzędzi AI. Każdy fakt na stronie ma źródło albo pochodzi z naszego testu.</li>
</ul>

<h2>Z czego się utrzymujemy</h2>
<p>Strona zarabia na linkach partnerskich do dostawców VPN. Dziś partnerami są __PARTNERS__. Prowizja nie wpływa na ranking ani na wyniki testów. Szczegóły są w części <a href="/jak-testujemy#linki">Linki partnerskie</a>.</p>

<h2>Kontakt i poprawki</h2>
<p>Napisz na adres <a href="mailto:kontakt@polskistreaming.pl">kontakt@polskistreaming.pl</a>. Jeśli znajdziesz błąd, poprawimy go i opiszemy zmianę w dzienniku zmian na stronie <a href="/jak-testujemy">Jak testujemy</a>.</p>
""", "prosec"),
    "page", [("/", "Polska telewizja za granicą"), ("/o-nas", "O nas")])

PAGES["/prywatnosc"] = ("Prywatność | Polski Streaming",
    "Polski Streaming nie używa plików cookie ani reklam śledzących. Liczymy tylko anonimowe odsłony stron.",
    band('<a href="/">Polska telewizja za granicą</a> / Prywatność', "Prywatność",
         "Krótko: nie ustawiamy plików cookie i nie śledzimy Cię między stronami.")
    + prose("""
<h2>Czego nie robimy</h2>
<ul>
  <li>Nie ustawiamy plików cookie.</li>
  <li>Nie używamy pikseli reklamowych ani narzędzi, które śledzą Cię na innych stronach.</li>
  <li>Nie ładujemy czcionek, ikon ani skryptów z cudzych serwerów. Wszystko jest na naszej domenie.</li>
</ul>
<h2>Statystyki odwiedzin</h2>
<p>Liczymy odsłony stron narzędziem Vercel Web Analytics. Działa ono bez plików cookie i z naszej domeny. Widzimy tylko liczby zbiorcze: którą stronę otwarto, z jakiego kraju, z jakiej strony ktoś przyszedł i na jakim typie urządzenia. Nie widzimy, kim jesteś, i nie rozpoznajemy Cię przy kolejnej wizycie następnego dnia.</p>
<h2>Kliknięcia w przyciski dostawców</h2>
<p>Gdy klikniesz przycisk prowadzący do dostawcy VPN, zapisujemy samo kliknięcie: którego dostawcy dotyczy, na której naszej stronie było, z jakiego kraju i na jakim typie urządzenia. Nie zapisujemy adresu IP ani niczego, co pozwala Cię rozpoznać.</p>
<h2>Powiadomienie o wizycie</h2>
<p>Przy pierwszej stronie, którą otworzysz, wysyłamy sobie krótkie powiadomienie: którą stronę otwarto, z jakiego kraju i miasta, na jakim typie urządzenia i z jakiej strony ktoś przyszedł. Niczego nie zapisujemy w bazie i nie wysyłamy adresu IP.</p>
<h2>Co widzi serwer</h2>
<p>Strona działa na serwerach firmy Vercel. Jak każdy serwer WWW zapisuje ona techniczne logi: adres IP, czas i adres otwartej strony. Nie łączymy tych danych z niczym innym.</p>
<h2>Linki do dostawców</h2>
<p>Przyciski „Strona dostawcy” prowadzą na strony firm VPN. Po kliknięciu obowiązuje ich polityka prywatności. Część z nich to linki partnerskie. Link partnerski prowadzi przez serwer sieci afiliacyjnej (CJ), która zapisuje kliknięcie, żeby przypisać zakup. Do linku dodajemy nazwę naszej strony, na której był przycisk, żeby wiedzieć, która strona doprowadziła do zakupu. My nie widzimy, kto kliknął ani kto kupił.</p>
""", "prosec"),
    "page", [("/", "Polska telewizja za granicą"), ("/prywatnosc", "Prywatność")])

EXTRA_CSS = """
.today{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px 28px;align-items:center;border:1px solid var(--line);border-left:4px solid var(--ok);background:var(--surface);border-radius:6px;padding:18px 20px;margin:0 0 28px}
.today.none{display:block;border-left-color:var(--warn)}.today.none p{margin:0}
.todayk{grid-column:1/-1;margin:0!important;font-size:14px;color:var(--muted)}
.todayh{display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px;align-items:center}
.todayh p{margin:0!important;max-width:none}.todayh b{display:block;font-size:17px;line-height:1.3;color:var(--ok)}.todayh span{display:block;font-size:13px;color:var(--muted);margin-top:2px}
.todayc{text-align:center}.todayc small{display:block;font-size:12px;color:var(--muted);margin-top:7px}
.pbh .affn{grid-column:-2/-1;margin-top:-14px}
.freecta .pcta .more{display:block;margin-top:12px;font-size:14px;color:var(--navy-muted)}
.mlist .affn{margin-top:6px}.mcta{padding:0 0 16px;border-bottom:1px solid var(--line)}.mlist .mcta .btn{margin-top:0}
.sbar{display:none}
a.btn[data-aff]{background:#D9480F;color:#fff}
.rrs5{border-top:2px solid var(--ink)}
.rr{display:grid;grid-template-columns:44px minmax(180px,1.1fr) 92px minmax(0,1.5fr) minmax(0,1.2fr) minmax(110px,.8fr) auto;gap:10px 22px;align-items:center;padding:20px 0;border-bottom:1px solid var(--line)}
.rrn{font:600 20px var(--mono,monospace);color:var(--muted)}.rr:first-child .rrn{color:#B7791F}
.rrb{display:flex;gap:12px;align-items:center}.rrb b{display:block;font-size:19px;line-height:1.2}
.rrtag{display:inline-block;margin-top:5px;font-size:12px;font-weight:600;background:#FFF1CC;color:#6B4A00;border-radius:4px;padding:2px 8px}
.rrs{text-align:center;line-height:1}.rrs b{font-size:30px;font-weight:700;color:var(--ok)}.rrs span{font-size:14px;color:var(--muted)}.rrs small{display:block;font-size:11px;color:var(--muted);margin-top:6px}
.rrp{list-style:none;margin:0;padding:0;font-size:13px;display:grid;gap:4px}.rrp li{display:flex;gap:7px;align-items:flex-start}.rrp svg{flex:none;color:var(--ok);margin-top:2px}
.rrt{display:block;font-size:13px}.rrt.ok{color:var(--ok)}.rrt.unstable{color:var(--warn)}.rrt.blocked{color:var(--bad)}.rrt.none{color:var(--none);font-weight:500}
.dbars{display:flex;gap:2px;margin-top:7px}.dbars i{flex:1;max-width:9px;height:20px;border-radius:2px;background:var(--ok)}.dbars i.unstable{background:var(--warn)}.dbars i.blocked{background:var(--bad)}.dbars i.none{background:var(--line)}
.dbl{display:block;font-size:11px;color:var(--muted);margin-top:4px}
.rrpr{line-height:1.25}.rrpr b{display:block;font:600 19px var(--mono,monospace)}.rrpr span{display:block;font-size:12px;color:var(--muted)}.rrpr em{display:block;font-style:normal;font-size:12px;font-weight:600;color:#C2410C;margin-top:4px}
.rr .pcta .btn{display:block;text-align:center}.rrmore{display:block;font-size:12px;margin-top:6px;color:var(--muted)}
.brand{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px 40px;align-items:center;margin-top:28px;border:1px dashed var(--muted);border-radius:8px;padding:22px 24px;background:var(--surface)}
.brandk{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}.brand h3{display:flex;gap:10px;align-items:center;margin:8px 0;font-size:20px}.brand p{margin:0;font-size:14px;color:var(--muted);max-width:76ch}
.brand .pcta b{display:block;font:600 20px var(--mono,monospace)}.brand .pcta span{display:block;font-size:12px;color:var(--muted);margin-bottom:10px}
.smx{border-top:2px solid var(--ink)}
.smrow{display:grid;grid-template-columns:minmax(190px,1.2fr) repeat(3,minmax(0,1fr)) minmax(120px,1fr) auto;gap:10px 22px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.smn{display:flex;gap:12px;align-items:center}.smn b{font-size:16px}.smc em{display:block;font-style:normal;font-size:12px;color:var(--muted);margin-bottom:2px}.smfree{font-size:13px}.smc .st{display:inline-flex;flex-wrap:wrap}.smc .st .stn{flex-basis:100%;margin-left:22px}
.deals{display:grid;gap:18px}.deal{border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:20px 22px}
.deal header{display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:14px;align-items:center}.deal h3{margin:0;font-size:20px}
.deal dl{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:0;margin:16px 0;font-size:14px}.deal dt,.deal dd{margin:0;padding:9px 0;border-top:1px solid var(--line)}.deal dt{color:var(--muted)}.deal dd{font-weight:500;text-align:right}
.deal .pcta .btn{display:block;text-align:center}
.sidefig a,#shot a{position:relative;display:block}.stamp{position:absolute;left:8px;bottom:8px;right:8px;width:fit-content;max-width:calc(100% - 16px);background:rgba(23,35,45,.88);color:#fff;font:500 11px var(--mono,monospace);padding:4px 8px;border-radius:4px}
@media (max-width:1180px){
  .rr{grid-template-columns:38px minmax(0,1fr) auto;gap:10px 14px}.rrp{display:none}.rrtest,.rrpr,.rr .pcta{grid-column:1/-1}.rrpr{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}.rrpr span,.rrpr em{margin:0}
  .brand{grid-template-columns:minmax(0,1fr)}.brand .pcta{text-align:left}
  .smrow{grid-template-columns:repeat(3,minmax(0,1fr))}.smn,.smb,.smrow .pcta{grid-column:1/-1}.smrow .pcta .btn{display:block;text-align:center}
  .deal header{grid-template-columns:44px minmax(0,1fr)}.deal header .rrpr{grid-column:1/-1}
}
.bfbar{background:var(--navy,#17232D);color:#fff}.bfbar .wrap{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;padding-top:14px;padding-bottom:14px;font-size:15px}
.bfbar b{background:#ffd77a;color:#17232D;padding:3px 9px;border-radius:4px;font-size:13px}.bfbar span{flex:1;min-width:220px;color:#dfe5ea}.bfbar a{color:#ffd77a;font-weight:600}
@media (max-width:760px){
  .today{grid-template-columns:minmax(0,1fr);padding:16px}.todayc .btn{display:block;text-align:center}
  .pbh .affn{grid-column:1/-1;margin-top:-6px}
  .sbar.on{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;gap:10px;align-items:center;background:var(--surface);border-top:1px solid var(--line);box-shadow:0 -8px 20px -14px rgba(23,35,45,.55);padding:10px 8px calc(10px + env(safe-area-inset-bottom)) 12px}
  .sbar span{flex:1;min-width:0;line-height:1.25}.sbar b{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sbar small{display:block;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sbar .btn{padding:10px 12px}.sbar button{background:none;border:0;font-size:22px;line-height:1;color:var(--muted);padding:6px;cursor:pointer}
  body.hasbar{padding-bottom:72px}
}
.affn{display:block;font-size:.72rem;color:var(--muted,#6b7280);margin-top:4px;text-align:center}
.disc{font-size:.82rem;color:var(--muted,#6b7280);margin:0 0 14px;max-width:70ch}
table.days td,table.days th{white-space:nowrap;text-align:left!important;padding-left:0}table.days th:first-child{font-weight:600}table.mini3.days{min-width:0;width:100%}@media (max-width:640px){table.days{font-size:12px}table.days td,table.days th{padding-right:6px}table.days .st svg{display:none}}

/* multi-page additions */
a.logo{color:var(--ink);text-decoration:none}
.cnav{gap:4px}
.cnav a{display:flex;align-items:center;font-size:15px;font-weight:500;color:var(--muted);text-decoration:none;padding:0 14px;border-bottom:3px solid transparent;border-top:3px solid transparent;white-space:nowrap}
.cnav a:hover{color:var(--ink)}
.cnav a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--ink)}
.crumb a{color:inherit}
.open.solo .otext{max-width:860px}
a.btn{text-decoration:none}
a.prov{text-decoration:none}
.narrowpad{padding-top:44px!important;padding-bottom:44px!important}
.after{margin-top:18px;font-size:14px;color:var(--muted)}
.svc{border-top:2px solid var(--ink)}
.svcrow{display:grid;grid-template-columns:30px minmax(160px,260px) 150px minmax(0,1fr) auto;gap:16px;align-items:center;padding:14px 0;border-bottom:1px solid var(--line)}
.svcrow img{width:30px;height:30px}
.svcrow .muted{font-size:14px}
.guides{background:var(--bg);border-bottom:1px solid var(--line)}
.guides .wrap{padding-top:48px;padding-bottom:52px}
.glist{list-style:none;margin:0;padding:0;border-top:2px solid var(--ink)}
.glist a{display:grid;grid-template-columns:minmax(0,420px) minmax(0,1fr) auto;gap:32px;align-items:baseline;padding:18px 0;border-bottom:1px solid var(--line);text-decoration:none;color:var(--ink)}
.glist a::after{content:"→";color:var(--muted)}
.glist b{font-size:20px;font-weight:600}
.glist span{color:var(--muted)}
.glist a:hover b{text-decoration:underline}
.prosec{background:var(--surface);border-bottom:1px solid var(--line)}
.prosec.alt{background:var(--grey)}
.prosec .wrap{padding-top:48px;padding-bottom:52px}
.prose{max-width:780px}
.prose h2{margin:36px 0 12px}
.prose h2:first-child{margin-top:0}
.prose h3{margin:26px 0 8px}
.prose p{margin:0 0 14px}
.prose ul{margin:0 0 14px;padding-left:20px;display:grid;gap:10px}
.prose blockquote{margin:18px 0;padding:18px 22px;background:var(--navy);color:var(--navy-ink);border-radius:8px;font-size:17px;line-height:1.5}
.note{border-left:4px solid var(--warn);background:var(--bg);padding:14px 18px;font-size:15px}
.prosec.alt .note{background:var(--surface)}
.pgrid{display:grid;grid-template-columns:minmax(0,780px) minmax(0,420px);gap:80px;justify-content:space-between;align-items:start}
.side2{position:sticky;top:24px}
.brief{border-top:2px solid var(--ink);padding-top:18px}
.brief dl{margin:12px 0 16px;display:grid;grid-template-columns:auto minmax(0,1fr);font-size:15px}
.brief dt,.brief dd{margin:0;padding:10px 0;border-bottom:1px solid var(--line)}
.brief dt{color:var(--muted);padding-right:20px}
.brief dd{font-weight:500;text-align:right}
.blinks{display:grid;gap:8px;font-size:15px}
.blinks a::after{content:" →"}
.sidefig{margin:0}
.sidefig img{display:block;width:100%;height:auto;border:1px solid var(--line)}
.figcap{font-size:13px;color:var(--muted);margin-top:8px}
.freecta{display:flex;flex-wrap:wrap;gap:24px 48px;align-items:center;justify-content:space-between;padding:44px 0}
.freecta h2{color:inherit;margin:0 0 10px}.freecta p{max-width:720px;margin:0;color:var(--navy-muted)}.freecta .btn{background:var(--surface);color:var(--ink)}
.cta2{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.btn.ghost{background:transparent;color:var(--cream-ink);border:1px solid var(--cream-ink)}
.lastrow{display:grid;grid-template-columns:30px minmax(160px,260px) minmax(0,1fr) auto;gap:16px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.lastrow img{width:30px;height:30px}
.lastrow .pst{display:inline-block;margin-right:22px;font-size:14px}
.egrid{grid-template-columns:minmax(0,760px) minmax(0,420px);justify-content:space-between}
.open.hasfig .wrap{grid-template-columns:minmax(0,1fr) minmax(0,640px);gap:56px;padding-top:36px;padding-bottom:36px}
.bframe{margin:0;border:1px solid #d9cfbf;border-radius:8px;overflow:hidden;background:#fff;box-shadow:0 18px 40px -22px rgba(23,35,45,.45)}
.bbar{display:flex;align-items:center;gap:6px;padding:9px 12px;background:#efe6d8;border-bottom:1px solid #d9cfbf}
.bbar i{width:9px;height:9px;border-radius:50%;background:#c9bda9}
.bbar span{margin-left:10px;font:400 12px var(--mono);color:#5A6570;background:#fff;border-radius:4px;padding:2px 10px;flex:1}
.bframe img{display:block;width:100%;height:auto}
.bframe figcaption{font-size:12px;color:#5A6570;padding:8px 12px;background:#fff;border-top:1px solid #e7dfd2}
.howflow{background:var(--surface);border-bottom:1px solid var(--line)}
.flow{display:grid;grid-template-columns:auto minmax(60px,1fr) auto minmax(60px,1fr) auto;align-items:center;gap:0;margin:22px 0 26px;padding:26px 28px;background:var(--bg);border:1px solid var(--line);border-radius:8px}
.prosec.alt .flow{background:var(--surface)}
.fnode{display:grid;justify-items:center;text-align:center;gap:4px;min-width:150px}
.fnode b{font-size:15px}
.fnode span{font-size:13px;color:var(--muted)}
.fico{height:54px;display:flex;align-items:center;justify-content:center;gap:4px;padding:0 14px;background:var(--surface);border:1px solid var(--line);border-radius:27px;margin-bottom:6px}
.fico img{display:block;border-radius:2px}
.fnode.mid .fico{border-color:var(--ok);box-shadow:0 0 0 4px color-mix(in srgb,var(--ok) 14%,transparent)}
.fline{position:relative;height:2px;margin:0 10px 44px;background:repeating-linear-gradient(90deg,var(--ok) 0 8px,transparent 8px 16px);background-size:16px 2px}
.fline span{position:absolute;left:50%;top:-22px;transform:translateX(-50%);font-size:11px;color:var(--muted);white-space:nowrap}
.fline::after{content:"";position:absolute;right:-2px;top:-4px;border-left:8px solid var(--ok);border-top:5px solid transparent;border-bottom:5px solid transparent}
.pstrip{border-top:2px solid var(--ink)}
.prow{display:grid;grid-template-columns:34px 170px minmax(0,1fr) minmax(0,1.3fr) minmax(0,1fr) auto;gap:20px;align-items:center;padding:14px 0;border-bottom:1px solid var(--line);font-size:14px;transition:background .2s}
.prow:hover{background:var(--zebra)}
.prow b{font-size:16px}
.pcta{text-align:center}
.prow em{display:block;font-style:normal;font-size:12px;color:var(--muted)}
.btn{transition:transform .15s ease,opacity .15s ease,box-shadow .15s ease}
.btn:hover{transform:translateY(-1px);box-shadow:0 6px 14px -8px rgba(23,35,45,.6)}
.btn:active{transform:translateY(0)}
.glist a{transition:background .2s,padding .2s}
.glist a:hover{background:var(--surface);padding-left:14px;padding-right:14px}
.glist a::after{transition:transform .2s}
.glist a:hover::after{transform:translateX(4px)}
.hero{transition:transform .6s ease}
@media (prefers-reduced-motion:no-preference){
  .fline{animation:dash 1.1s linear infinite}
  .js .rv{opacity:0;transform:translateY(16px);transition:opacity .5s ease,transform .5s ease}
  .js .rv.in{opacity:1;transform:none}
  .js .pb.rv.in{transition:opacity .5s ease,transform .22s ease,box-shadow .22s ease,border-color .22s ease}
  .pb:hover,.js .pb.rv.in:hover{transform:translateY(-3px)}
  .open .otext>*{animation:rise .55s ease both}
  .open .otext>*:nth-child(2){animation-delay:.05s}.open .otext>*:nth-child(3){animation-delay:.1s}.open .otext>*:nth-child(4){animation-delay:.15s}
  .open .hero,.open .bframe{animation:rise .7s ease .1s both}
}
@keyframes dash{to{background-position:16px 0}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.answer{font-size:18px;border-left:4px solid var(--ok);background:var(--bg);padding:16px 20px;margin-bottom:28px!important}
.when a{color:inherit}
table.mini{width:100%;min-width:0;font-size:15px;margin:0 0 10px;border-top:2px solid var(--ink)}
table.mini th{text-align:left;font-weight:400;color:var(--muted);padding:10px 20px 10px 0;border-bottom:1px solid var(--line);width:42%;height:auto;position:static;background:none}
table.mini td{height:auto;padding:10px 0;border-bottom:1px solid var(--line);font-weight:500;text-align:left!important}
table.mini3{width:100%;min-width:560px;font-size:14px;border-top:2px solid var(--ink);margin-bottom:14px}
table.mini3 th{position:static;background:none;height:auto;padding:10px 16px 10px 0;border-top:0}
table.mini3 td{height:auto;padding:12px 16px 12px 0;vertical-align:top;text-align:left!important}
table.mini3 td:first-child{font-weight:600;width:30%}
.small{font-size:13px}
.tvico{color:var(--ink)}
.hero.art{align-self:center;border-radius:0;-webkit-mask-image:linear-gradient(to right,transparent 0,#000 14%,#000 92%,transparent 100%);mask-image:linear-gradient(to right,transparent 0,#000 14%,#000 92%,transparent 100%)}
.btn.big{font-size:16px;padding:14px 22px;border-radius:6px}
.svcbar{background:var(--surface);border-bottom:1px solid var(--line)}
.svcbar .wrap{display:flex;flex-wrap:wrap;align-items:center;gap:14px 22px;padding-top:16px;padding-bottom:16px;font-size:14px;color:var(--muted)}
.svcbar a{text-decoration:none;transition:transform .15s}
.svcbar a:hover{transform:translateY(-2px)}
.hls{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--line);gap:1px}
.hl{display:grid;gap:8px;align-content:start;padding:20px;background:var(--surface);text-decoration:none;color:var(--ink);transition:background .2s}
.hl:hover{background:var(--zebra)}
.hlk{font-size:12px;font-weight:600;color:var(--accent);text-transform:none}
.hlv{display:flex;align-items:center;gap:10px;font-size:19px;font-weight:700}
.hld{font-size:14px;color:var(--muted)}
.disc{background:var(--bg);border-bottom:1px solid var(--line);font-size:12px;color:var(--muted)}
.disc .wrap{padding-top:5px;padding-bottom:5px}
.disc a{color:var(--muted)}
.feat{background:var(--navy);color:var(--navy-ink)}
.feat .wrap{padding-top:36px;padding-bottom:36px}
.featbox{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) auto;gap:48px;align-items:center}
.feattag{display:inline-block;font-size:12px;font-weight:600;color:#ffd77a;border:1px solid #ffd77a;border-radius:20px;padding:3px 12px;margin-bottom:12px}
.feath h2{display:flex;align-items:center;gap:14px;font-size:34px}
.feath h2 img{background:#fff;border-radius:9px;padding:6px}
.feath p{color:var(--navy-muted);margin-top:10px;max-width:560px}
.feattest{margin-top:14px;font-size:14px}.feattest .pst{display:inline-block;margin-right:16px;color:inherit}
.featl{list-style:none;margin:0;padding:0;display:grid;gap:10px;font-size:15px}
.featl li{display:grid;grid-template-columns:16px minmax(0,1fr);gap:10px;align-items:center}
.featl svg{color:#55d3a4}
.featcta{display:grid;justify-items:center;gap:2px;text-align:center}
.featcta b{font:500 34px/1.1 var(--mono);letter-spacing:-.02em}
.featcta span{font-size:12px;color:var(--navy-muted);margin-bottom:10px}
.featcta .btn{background:#ffd77a;color:#17232D}
.featcta small{font-size:11px;color:var(--navy-muted);margin-top:8px;max-width:220px}
.pblist{display:grid;gap:20px}
.affnote{display:block;font-size:11px;color:var(--muted);text-align:center;margin-top:5px}
.pbh .btn+.affnote{grid-column:-2/-1;margin-top:-14px}
.rank{display:grid;place-items:center;width:44px;height:44px;border-radius:50%;background:var(--ink);color:var(--surface);font:600 20px var(--mono)}
.badge.gold{color:#8a5a00;border-color:#d9a520;background:#fff6da}
table.pts td,table.pts th{text-align:center!important}
table.pts td:first-child,table.pts th:first-child{text-align:left!important;width:auto;font-weight:400}
.pb{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden;transition:border-color .2s,box-shadow .2s}
.pb:hover{border-color:var(--none);box-shadow:0 14px 34px -24px rgba(23,35,45,.5)}
.pbh{display:grid;grid-template-columns:44px 48px minmax(0,1fr) auto auto;gap:20px;align-items:center;padding:22px 24px}
.pbh h3{font-size:24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.pbh p{color:var(--muted);font-size:15px;margin-top:2px}
.badge{font-size:12px;font-weight:600;color:var(--ok);border:1px solid var(--ok);border-radius:20px;padding:2px 10px;white-space:nowrap}
.pbprice{text-align:right;padding-right:8px}
.pbprice b{display:block;font:500 28px/1.1 var(--mono);letter-spacing:-.02em;white-space:nowrap}
.pbprice span{font-size:12px;color:var(--muted)}
.pbfacts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--bg)}
.pbfacts>div{padding:14px 24px;border-right:1px solid var(--line)}
.pbfacts>div:last-child{border-right:0}
.pbfacts span{display:block;font-size:12px;color:var(--muted)}
.pbfacts b{font-size:15px;font-weight:600}
.pbfacts .pst{display:inline-block;margin-right:14px;font-weight:400}
.pbbody{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.1fr);gap:32px;padding:20px 24px 24px}
.pbbody h4{margin:0 0 10px;font-size:13px;font-weight:600;color:var(--muted)}
.pbbody ul{list-style:none;margin:0;padding:0;display:grid;gap:8px;font-size:15px}
.pbbody li{display:grid;grid-template-columns:16px minmax(0,1fr);gap:10px;align-items:start}
.pbbody li svg{margin-top:4px}
.pros svg{color:var(--ok)}.cons svg{color:var(--none)}
.pbbody p{font-size:14px;margin:0 0 8px}
.pbbody .apps,.pbbody .src{color:var(--muted);font-size:13px}
.pblist.compact .pbbody{display:none}
.quizsec{background:var(--navy);color:var(--navy-ink)}
.quiz{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:20px 56px;align-items:start}
.qhead{grid-row:span 4}
.qhead p{color:var(--navy-muted);margin-top:8px}
.qstep h3{font-size:17px;margin-bottom:12px}
.qopts{display:flex;flex-wrap:wrap;gap:10px}
.qopts button{font-size:15px;font-weight:500;background:transparent;color:var(--navy-ink);border:1px solid var(--navy-line);border-radius:6px;padding:11px 16px;cursor:pointer;transition:background .15s,border-color .15s}
.qopts button:hover{background:var(--navy-2);border-color:var(--navy-muted)}
.qopts button[aria-pressed="true"]{background:var(--navy-ink);color:var(--navy);border-color:var(--navy-ink)}
.qres{background:var(--navy-2);border:1px solid var(--navy-line);border-radius:8px;padding:20px 22px;display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:16px;align-items:center}
.qres img{width:44px;height:44px;background:#fff;border-radius:8px;padding:6px}
.qres b{display:block;font-size:20px}
.qres span{color:var(--navy-muted);font-size:14px}
.qres .btn{background:var(--navy-ink);color:var(--navy)}
.qres .again{grid-column:1/-1;font-size:13px;color:var(--navy-muted);background:none;border:0;padding:0;text-align:left;cursor:pointer;text-decoration:underline}
.devsec{background:var(--cream);color:var(--cream-ink);border-bottom:1px solid var(--line)}
.devsec .wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,640px);gap:48px;align-items:center;padding-top:44px;padding-bottom:44px}
.devtext p{color:var(--cream-muted);margin-top:8px;max-width:560px}
.devlist{list-style:none;margin:18px 0 12px;padding:0;border-top:2px solid var(--cream-ink);max-width:620px}
.devlist li{display:grid;grid-template-columns:120px minmax(0,1fr);gap:16px;padding:10px 0;border-bottom:1px solid #e3d8c7;font-size:15px}
.devlist span{color:var(--cream-muted)}
.devimg{display:block;width:100%;height:auto;-webkit-mask-image:linear-gradient(to right,transparent 0,#000 10%,#000 94%,transparent 100%);mask-image:linear-gradient(to right,transparent 0,#000 10%,#000 94%,transparent 100%)}
.devsec .muted{color:var(--cream-muted)}
.scrollx{overflow-x:auto}
.monly{display:none}
table.facts{min-width:980px}
table.facts td{height:auto;padding-top:16px;padding-bottom:16px;vertical-align:middle}
table.facts td:last-child,table.facts th:last-child{text-align:right}
.pst{display:block;font-size:13px;white-space:nowrap}
.pst .st{margin-left:4px}
.provgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 64px}
.provsec{border-top:2px solid var(--ink);padding:22px 0 30px}
.provsec h3{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.kv{margin:0 0 14px;display:grid;grid-template-columns:200px minmax(0,1fr);font-size:15px}
.kv dt,.kv dd{margin:0;padding:9px 0;border-bottom:1px solid var(--line)}
.kv dt{color:var(--muted)}
.provsec p{margin:0 0 12px;font-size:14px}
@media (max-width:1180px){.featbox{grid-template-columns:minmax(0,1fr);gap:24px}.featcta{justify-items:start;text-align:left}.hls{grid-template-columns:repeat(2,minmax(0,1fr))}.pbh{grid-template-columns:44px 48px minmax(0,1fr) auto}.pbh .btn{grid-column:1/-1;text-align:center}.pbfacts{grid-template-columns:repeat(2,minmax(0,1fr))}.pbfacts>div{border-bottom:1px solid var(--line)}.pbfacts>div:nth-child(2n){border-right:0}.pbbody{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.pbbody>div:last-child{grid-column:1/-1}.quiz{grid-template-columns:minmax(0,1fr)}.qhead{grid-row:auto}.devsec .wrap{grid-template-columns:minmax(0,1fr)}.open.hasfig .wrap{grid-template-columns:minmax(0,1fr) minmax(0,460px)}.prow{grid-template-columns:34px 150px minmax(0,1fr) minmax(0,1fr) auto}.prow>span:nth-of-type(3){display:none}.egrid{grid-template-columns:minmax(0,1fr)}.pgrid{grid-template-columns:minmax(0,1fr);gap:32px}.side2{position:static;max-width:520px}.cnav{overflow-x:auto}.provgrid{grid-template-columns:minmax(0,1fr)}}
@media (max-width:820px){
  .hls{grid-template-columns:minmax(0,1fr)}.pbh{grid-template-columns:36px 40px minmax(0,1fr);gap:12px 12px;padding:18px}.rank{width:36px;height:36px;font-size:16px}.pbh h3{font-size:20px}.pbprice{grid-column:1/-1;text-align:left;display:flex;align-items:baseline;gap:8px}.pbfacts>div{padding:12px 18px}.pbbody{grid-template-columns:minmax(0,1fr);gap:20px;padding:18px}.qres{grid-template-columns:44px minmax(0,1fr)}.qres .btn{grid-column:1/-1;text-align:center}.hero.art{-webkit-mask-image:none;mask-image:none}
  .open.hasfig .wrap{grid-template-columns:minmax(0,1fr);gap:8px;padding-bottom:24px}
  .flow{grid-template-columns:minmax(0,1fr);justify-items:center;padding:20px}.fline{width:2px;height:34px;margin:8px 0;background:repeating-linear-gradient(180deg,var(--ok) 0 8px,transparent 8px 16px);animation:none}.fline span{left:14px;top:8px;transform:none}.fline::after{right:-4px;top:auto;bottom:-2px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:8px solid var(--ok);border-bottom:0}
  .prow{grid-template-columns:34px minmax(0,1fr);gap:6px 12px}.prow>span,.prow>a{grid-column:2}.prow>a{justify-self:start}
  .lastrow{grid-template-columns:30px minmax(0,1fr);gap:6px 12px}.lastrow>span{grid-column:2}
  .scrollx{display:none}.scrollx.keep{display:block}.monly{display:block}
  .cnav a{padding:10px 12px}
  .svcrow{grid-template-columns:30px minmax(0,1fr) auto;gap:6px 12px}
  .svcrow .muted,.svcrow a{grid-column:2/-1}
  .glist a{grid-template-columns:minmax(0,1fr) auto;gap:4px 12px}
  .glist span{grid-column:1/-1;grid-row:2}
  .glist b{font-size:17px}
  .kv{grid-template-columns:minmax(0,1fr)}
  .kv dt{border-bottom:0;padding-bottom:0}
}
/* ---- 19.11.2026 structure pass: narrower page, cards, home hero ---- */
h1,h2,h3,.logo,.rrb b,.smn b,.deal h3,.todayh b,.brand h3{font-family:"Manrope",var(--sans);letter-spacing:-.015em}
h1{font-weight:800;letter-spacing:-.012em;word-spacing:.04em}h2{font-weight:800;letter-spacing:-.008em}h3{font-weight:700;letter-spacing:0}
.wrap{max-width:1480px}
.disc{background:none;border:0;font-size:12px;color:var(--muted);margin:0 0 16px;max-width:86ch;padding:0}
.results.soft{background:var(--bg)}
.rrs5{border-top:0;display:grid;gap:12px}
.rr{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 22px;box-shadow:0 1px 2px rgba(23,35,45,.05);position:relative;transition:box-shadow .2s,transform .2s}
.rr:hover{box-shadow:0 10px 24px -16px rgba(23,35,45,.45);transform:translateY(-1px)}
.rr.first{border:2px solid #E0A526;padding-top:26px}
.rrib{position:absolute;top:-11px;left:20px;background:#E0A526;color:#17232D;font-size:12px;font-weight:700;border-radius:4px;padding:2px 10px}
.sm{background:var(--navy,#17232D);color:var(--navy-ink,#EDF1F4);border-bottom:0}
.sm .wrap{padding-top:56px;padding-bottom:52px}
.smtop{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:28px 56px;align-items:end;margin-bottom:28px}
.smtop h2{color:#fff;font-size:30px;margin:12px 0 8px}.smtop p{color:var(--navy-muted,#A0ADB8);max-width:62ch}
.smlive{display:inline-flex;gap:9px;align-items:center;font:600 12px var(--mono,monospace);text-transform:uppercase;letter-spacing:.06em;color:#4CCB83}
.smlive i{width:9px;height:9px;border-radius:50%;background:#4CCB83;box-shadow:0 0 0 0 rgba(76,203,131,.6);animation:smp 2s infinite}
@keyframes smp{70%{box-shadow:0 0 0 9px rgba(76,203,131,0)}100%{box-shadow:0 0 0 0 rgba(76,203,131,0)}}
@media (prefers-reduced-motion:reduce){.smlive i{animation:none}}
.smnums{display:grid;grid-template-columns:repeat(3,minmax(0,150px));gap:12px}
.smnums div{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:14px 16px}
.smnums b{display:block;font:600 26px var(--mono,monospace);color:#fff}.smnums span{display:block;font-size:12px;color:var(--navy-muted,#A0ADB8);margin-top:4px;line-height:1.35}
.smx{border:1px solid rgba(255,255,255,.12);border-radius:12px;background:rgba(255,255,255,.035);padding:0 24px}
.sm .smrow{border-bottom:1px solid rgba(255,255,255,.1);padding:18px 0;grid-template-columns:minmax(210px,1.3fr) repeat(3,minmax(0,1fr)) minmax(150px,1.1fr) 240px}
.sm .smrow:last-child{border-bottom:0}
.smhead{padding:14px 0!important;font:600 12px var(--mono,monospace);text-transform:uppercase;letter-spacing:.05em;color:var(--navy-muted,#A0ADB8)}
.smh{display:inline-flex;gap:8px;align-items:center}.smh img{display:block;width:auto;background:#fff;border-radius:4px;padding:3px 5px;box-sizing:content-box}
.sm .smn b{color:#fff;font-size:17px;display:block}.sm .smn small{display:block;font-size:12px;color:var(--navy-muted,#A0ADB8)}
.sm .smc em{display:none}.sm .smc small{display:block;font-size:11px;color:var(--navy-muted,#A0ADB8);margin-top:5px}
.pill{display:inline-flex;gap:7px;align-items:center;font-size:14px;font-weight:600;border-radius:999px;padding:6px 13px 6px 10px;background:rgba(76,203,131,.16);color:#5FDD95}
.pill.unstable{background:rgba(231,182,91,.16);color:#E7B65B}.pill.blocked{background:rgba(240,120,120,.16);color:#F07878}.pill.none{background:rgba(255,255,255,.07);color:#A0ADB8}
.sm .dbars i{height:26px;max-width:12px;background:#4CCB83}.sm .dbars i.unstable{background:#E7B65B}.sm .dbars i.blocked{background:#F07878}.sm .dbars i.none{background:rgba(255,255,255,.14)}
.sm .dbl,.sm .affn{color:var(--navy-muted,#A0ADB8)}.sm .pcta{text-align:right}.sm .pcta .btn{display:inline-block}.sm .affn{text-align:right}
.sm .smfree{color:#9CC2FF;font-size:13px}
.smafter{margin-top:18px;font-size:14px;color:var(--navy-muted,#A0ADB8)}.smafter a{color:#9CC2FF}
.ggc{border-top:3px solid var(--accent)}.ggc.g1{border-top-color:var(--warn)}.ggc.g2{border-top-color:var(--ok)}
.ggc h3{display:flex;gap:8px;align-items:center}.ggc h3 svg{color:var(--accent)}.ggc.g1 h3 svg{color:var(--warn)}.ggc.g2 h3 svg{color:var(--ok)}
.guides{background:var(--surface)}.howflow{background:var(--cream)}
.hw{background:var(--cream);border-bottom:1px solid var(--line)}.hw .wrap{padding-top:56px;padding-bottom:52px}
.hwg{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:48px;align-items:center}
.hws{list-style:none;margin:0;padding:0;display:grid;gap:14px;position:relative}
.hws:before{content:"";position:absolute;left:35px;top:36px;bottom:36px;border-left:2px dashed var(--ok);opacity:.55}
.hws li{position:relative;display:grid;grid-template-columns:36px 44px minmax(0,1fr);gap:14px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px 18px 18px;box-shadow:0 1px 2px rgba(23,35,45,.05)}
.hwn{width:36px;height:36px;border-radius:50%;background:var(--ok);color:#fff;font:700 16px var(--mono,monospace);display:grid;place-items:center;position:relative;z-index:1}
.hwi{width:44px;height:44px;border-radius:10px;background:rgba(22,131,74,.1);color:var(--ok);display:grid;place-items:center}
.hws h3{font-size:17px;margin:0 0 4px}.hws p{font-size:14px;color:var(--muted);margin:0;line-height:1.5}
.hwba{display:grid;grid-template-columns:minmax(0,1fr) 40px minmax(0,1fr);gap:12px;align-items:center}
.hwf{margin:0;position:relative;background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:0 14px 30px -22px rgba(23,35,45,.55)}
.hwf img{display:block;width:100%;height:auto;aspect-ratio:16/10;object-fit:cover}
.hwf figcaption{font-size:12px;color:var(--muted);padding:10px 14px;line-height:1.45}
.hwtag{position:absolute;top:10px;left:10px;font-size:12px;font-weight:700;border-radius:999px;padding:4px 11px;color:#fff;background:var(--bad)}
.hwf.good .hwtag{background:var(--ok)}.hwf.bad{border-color:rgba(194,59,59,.45)}.hwf.good{border-color:rgba(22,131,74,.55)}
.hwarrow{width:40px;height:40px;border-radius:50%;background:var(--ok);color:#fff;display:grid;place-items:center}
@media (max-width:1180px){.hwg{grid-template-columns:minmax(0,1fr);gap:28px}}
@media (max-width:620px){.hwba{grid-template-columns:minmax(0,1fr)}.hwarrow{margin:0 auto;transform:rotate(90deg)}.hw .wrap{padding-top:40px;padding-bottom:40px}.hws li{grid-template-columns:32px minmax(0,1fr);padding:16px}.hwi{display:none}.hwn{width:32px;height:32px}.hws:before{left:31px}}
.hh .wrap{grid-template-columns:minmax(0,1fr) minmax(0,560px);gap:40px;min-height:0;padding-bottom:34px}
.hh .otext{padding:44px 0 30px}.hh h1{font-size:40px}
.hhk{display:inline-flex;gap:7px;align-items:center;font-size:13px;font-weight:600;color:var(--ok);background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:5px 12px;margin-bottom:16px}
.hhl{list-style:none;margin:18px 0 0;padding:0;display:grid;gap:7px;font-size:15px}.hhl li{display:flex;gap:9px;align-items:center}.hhl svg{color:var(--ok);flex:none}
.pickw{background:var(--cream);border-bottom:1px solid var(--line)}.hh{border-bottom:0}
.rr{grid-template-columns:40px minmax(220px,1.3fr) 80px minmax(0,1.4fr) minmax(150px,1fr) 120px 176px!important}
.pick{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 20px;box-shadow:0 8px 22px -18px rgba(23,35,45,.5);margin:0 0 26px}
.pick b{font-size:15px}.pick div{display:flex;flex-wrap:wrap;gap:8px}
.pick a{display:inline-flex;gap:8px;align-items:center;font-size:14px;font-weight:600;color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:8px 12px;background:var(--surface);transition:border-color .15s,background .15s}
.pick a:hover{border-color:var(--ink);background:var(--zebra)}.pick img{display:block;width:auto}
.gg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;align-items:start}
.ggc{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:4px 20px 8px}
.ggc h3{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:16px 0 10px}
.ggc a{display:block;padding:13px 0;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}
.ggc a b{display:block;font-size:15px;line-height:1.35}.ggc a span{display:block;font-size:13px;color:var(--muted);margin-top:3px}.ggc a:hover b{color:var(--accent);text-decoration:underline}
.deal,.brand,.today{border-radius:10px}
@media (max-width:1180px){.rr{grid-template-columns:38px minmax(0,1fr) auto!important}.gg{grid-template-columns:minmax(0,1fr)}.hh .wrap{grid-template-columns:minmax(0,1fr) minmax(0,420px)}}
@media (max-width:820px){.hh .wrap{grid-template-columns:minmax(0,1fr);padding-bottom:20px}.hh h1{font-size:30px}.hh .otext{padding:26px 0 8px}.pick{margin:0 0 16px}.rr{padding:16px}.rr.first{padding-top:24px}.smx{padding:0 14px}}
@media (max-width:1180px){.smtop{grid-template-columns:minmax(0,1fr)}.smhead{display:none!important}.sm .smrow{grid-template-columns:repeat(3,minmax(0,1fr))}.sm .smc em{display:block;color:var(--navy-muted,#A0ADB8)}.sm .pcta,.sm .affn{text-align:center}.sm .pcta .btn{display:block}}
@media (max-width:560px){.smnums{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.smnums div{padding:10px}.smnums b{font-size:20px}.smtop h2{font-size:24px}.pill{font-size:13px;padding:5px 10px 5px 8px}.sm .wrap{padding-top:40px;padding-bottom:40px}}
"""


def build_js():
    s = (HERE / "app.src.js").read_text()

    def rep(a, b):
        nonlocal s
        assert a in s, a[:70]
        s = s.replace(a, b)

    rep("var $=function(id){return document.getElementById(id)};",
        "var DUMMY=document.createElement('div');var $=function(id){return document.getElementById(id)||DUMMY};\n"
        "  var LINK=" + json.dumps({**AFF, "protonfree": AFF["proton"], "cybr": "https://www.cyberghostvpn.com"}) + ";\n"
        "  var SHORT={nord:'NordVPN',proton:'Proton VPN Plus',protonfree:'Proton VPN, darmowy'};function nm(p){return SHORT[p.id]||p.name}\n"
        "  var ORD=['nord','proton','protonfree'];function ord(p){var i=ORD.indexOf(p.id);return i<0?9:i}\n"
        "  function offer(p,t){var a=p.id==='protonfree'?'proton':p.id;return '<a class=\"btn\" href=\"'+LINK[p.id]+'\" target=\"_blank\" rel=\"sponsored nofollow noopener\" data-aff=\"'+a+'\">'+t+'</a>'}")
    rep("var PRICE={proton:['0 zł','plan darmowy']};", "var PRICE={proton:['płatny','konto testowe'],protonfree:['darmowy','0 zł'],nord:['płatny','konto testowe']};")
    rep("'<td><button class=\"btn\" type=\"button\" data-cta aria-label=\"Sprawdź ofertę '+esc(p.name)+'\">Sprawdź ofertę</button></td></tr>'",
        "'<td>'+offer(p,'Zobacz ofertę')+'</td></tr>'")
    rep("'<button class=\"btn\" type=\"button\" data-cta>Sprawdź ofertę '+esc(p.name)+'</button></details>'",
        "'</details>'+(p.id==='protonfree'?'':'<div class=\"mcta\">'+offer(p,'Zobacz ofertę '+esc(nm(p)))+'<small class=\"affn\">Link partnerski</small></div>')")
    rep("<th>Cena za miesiąc</th><th>Oferta partnera</th>", "<th>Plan w teście</th><th>Oferta</th>")
    rep("<div><span>Cena za miesiąc</span>", "<div><span>Plan w teście</span>")
    rep("$('scope').textContent='Testujemy na razie '+tested.length+' z '+RUN.providers.length+' dostawców i '+SVON.length+' darmowe serwisy. Płatnych serwisów (Polsat Box Go, Canal+ Online) jeszcze nie testujemy.';",
        "$('scope').textContent='Każdego ranka sprawdzamy '+tested.length+' plany VPN z '+SVON.length+' serwisami: '+SVON.map(function(s){return s.name}).join(', ')+'. Polsat Box Go i Canal+ Online wymagają płatnego konta i nie są jeszcze w teście.';")
    rep("'<span>'+esc(p.name)+'<small>'+sub+'</small></span></button></td>'", "'<span>'+esc(nm(p))+'<small>'+sub+'</small></span></button></td>'")
    rep("'<b>'+esc(p.name)+'<small>'+sub+'</small></b><span", "'<b>'+esc(nm(p))+'<small>'+sub+'</small></b><span")
    rep("return works(b)-works(a)||(b.speed_mbps||0)-(a.speed_mbps||0);", "return works(b)-works(a)||ord(a)-ord(b);")
    rep("<button type=\"button\" data-hp=\"'+p.id+'\">'+esc(p.name)+'</button><div class=\"cells\" role=\"img\"", "<button type=\"button\" data-hp=\"'+p.id+'\">'+esc(nm(p))+'</button><div class=\"cells\" style=\"grid-template-columns:repeat('+N+',1fr)\" role=\"img\"")
    rep("return '<button type=\"button\" data-hp=\"'+p.id+'\">'+esc(p.name)+'</button>'}).join('');", "return '<button type=\"button\" data-hp=\"'+p.id+'\">'+esc(nm(p))+'</button>'}).join('');")
    # The chart shows only the days since the first test (10 to 30), so the line is not pushed off the phone screen.
    rep("var days=[];for(var i=29;i>=0;i--)days.push(addDays(RUN.date,-i));",
        "var first=Object.keys(HIST.days).sort()[0]||RUN.date,N=Math.min(30,Math.max(10,Math.round((new Date(RUN.date)-new Date(first))/864e5)+1));var days=[];for(var i=N-1;i>=0;i--)days.push(addDays(RUN.date,-i));")
    rep("return L+pw*(i+.5)/30}", "return L+pw*(i+.5)/N}")
    rep("[0,7,14,21,29].forEach(function(i){", "[0,Math.round((N-1)/3),Math.round((N-1)*2/3),N-1].forEach(function(i){")
    rep("(x(i)-pw/60+2)", "(x(i)-pw/(2*N)+2)")
    rep("width=\"'+(pw/30-4)+'\"", "width=\"'+(pw/N-4)+'\"")
    rep("dm(days[15])", "dm(days[Math.floor(N/2)])")
    rep("dm(days[29])", "dm(days[N-1])")
    rep("$('s1').textContent=tested.filter(function(p){return stat(p,'tvpvod')==='ok'}).length+'/'+tested.length;", "$('s1').textContent=tested.filter(function(p){var x=stat(p,'tvpvod');return x==='ok'||x==='okr'}).length+'/'+tested.length;var sb=document.querySelector('.sortbar');if(sb&&tested.length<2)sb.style.display='none';")
    rep("data=sorted(),tested=RUN.providers.filter(function(p){return p.tested});", "tested=RUN.providers.filter(function(p){return p.tested}),data=sorted().filter(function(p){return p.tested});")
    rep("    RUN.providers.forEach(function(p){\n      var o=0,t=0,cells='';", "    RUN.providers.filter(function(p){return p.tested}).forEach(function(p){\n      var o=0,t=0,cells='';")
    rep("$('hprov').innerHTML=RUN.providers.map(", "$('hprov').innerHTML=RUN.providers.filter(function(p){return p.tested}).map(")
    rep("    render();\n  }",
        "    all('[data-svc]',function(el){var sid=el.dataset.svc,h='';RUN.providers.filter(function(p){return p.tested}).forEach(function(p){var r=p.services[sid];if(!r)return;"
        "h+='<div class=\"svcrow\">'+logo(p.id)+'<b>'+esc(p.name)+(p.plan?' ('+esc(p.plan)+')':'')+'</b>'+st(stat(p,sid))+'<span class=\"muted\">Test: '+fmtDT(r.tested_at)+(r.reason&&stat(p,sid)!=='okr'?'. '+esc(r.reason):'')+'</span>'"
        "+(r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\">zrzut ekranu</a>':'<span></span>')+'</div>'});"
        "el.innerHTML=h||'<p class=\"muted\" style=\"padding:14px 0\">Tego serwisu jeszcze nie testujemy.</p>'});\n"
        "    all('[data-prov-status]',function(el){var p=RUN.providers.filter(function(x){return x.id===el.dataset.provStatus})[0];"
        "el.innerHTML=p&&p.tested?SVON.map(function(s){return '<span class=\"pst\">'+esc(s.name)+':'+st(stat(p,s.id))+'</span>'}).join(''):st('none')});\n"
        "    all('[data-last]',function(el){var h='';RUN.providers.filter(function(p){return p.tested}).forEach(function(p){"
        "h+='<div class=\"lastrow\">'+logo(p.id)+'<b>'+esc(p.name)+(p.plan?' ('+esc(p.plan)+')':'')+'</b><span>'+SVON.map(function(s){return '<span class=\"pst\">'+esc(s.name)+':'+st(stat(p,s.id))+'</span>'}).join('')+'</span><span class=\"muted\">Test: '+fmtDT(RUN.finished_at)+'</span></div>'});el.innerHTML=h});\n"
        "    all('[data-shot]',function(el){var p=best(),r=p&&p.services&&p.services[el.dataset.shot];el.innerHTML=r&&r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"/'+esc(r.shot)+'\" alt=\"Zrzut ekranu z testu\" loading=\"lazy\" width=\"1440\" height=\"900\"><span class=\"stamp\">Zweryfikowano: '+fmtDT(r.tested_at)+' · '+esc(nm(p))+', serwer w Polsce</span></a>':''});\n"
        "    render();\n  }")
    rep("get('data/latest.json'),get('data/history.json')", "get('/data/latest.json'),get('/data/history.json')")
    rep("proton:'https://cdn.simpleicons.org/protonvpn',nord:'https://cdn.simpleicons.org/nordvpn',surf:'https://cdn.simpleicons.org/surfshark',expr:'https://cdn.simpleicons.org/expressvpn'",
        "proton:'/logos/proton.svg',protonfree:'/logos/proton.svg',nord:'/logos/nord.svg',surf:'/logos/surf.svg',expr:'/logos/expr.svg'")
    rep("https://flagcdn.com/", "/flags/")
    for old in ["'logos/tvpvod.png'", "'logos/player.svg'", "'logos/polsat.svg'", "'logos/canal.svg'", "'logos/cyberghost-icon.png'"]:
        rep(old, "'/" + old[1:])
    rep("' przez '+esc(top.name)+'\" width=\"1440\" height=\"900\"></a>'", "' przez '+esc(top.name)+'\" width=\"1440\" height=\"900\"><span class=\"stamp\">Zweryfikowano: '+fmtDT(r.tested_at)+' · '+esc(nm(top))+', serwer w Polsce</span></a>'")
    rep("'<img class=\"t\" src=\"'+esc(rr.shot)+'\"", "'<img class=\"t\" src=\"/'+esc(rr.shot)+'\"")
    rep("'<a href=\"'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"'+esc(r.shot)+'\"", "'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"/'+esc(r.shot)+'\"")
    s += """
(function(){
  var q=document.getElementById('quiz');if(!q)return;
  var P={proton:['Proton VPN','/logos/proton.svg','https://protonvpn.com'],nord:['NordVPN','/logos/nord.svg','https://nordvpn.com'],surf:['Surfshark','/logos/surf.svg','https://surfshark.com'],expr:['ExpressVPN','/logos/expr.svg','https://www.expressvpn.com'],cybr:['CyberGhost','/logos/cyberghost-icon.png','https://www.cyberghostvpn.com']};
  var a={},order=['pay','dev','prio'];
  function step(n){return q.querySelector('[data-q="'+n+'"]')}
  function pick(){
    if(a.pay==='free')return ['proton','Jedyny w zestawieniu z darmowym serwerem w Polsce. Plan darmowy działa na jednym urządzeniu, a kraj trzeba ustawić ręcznie.','/darmowy-vpn-polska-telewizja','Jak ustawić darmowy serwer'];
    if(a.dev==='many')return ['surf','Jedyny w zestawieniu bez limitu urządzeń. ExpressVPN pozwala na 14.'];
    if(a.prio==='price')return ['proton','Najniższa cena w zestawieniu: 6,29 zł za miesiąc w planie na 2 lata.'];
    if(a.prio==='pl')return ['nord','Podaje 61 serwerów w Polsce, najwięcej w zestawieniu. Gdy jeden jest zablokowany, łatwiej zmienić na inny.'];
    return ['cybr','Daje 45 dni na zwrot pieniędzy, najdłużej w zestawieniu. Masz czas, żeby sprawdzić go ze swoim serwisem.'];
  }
  function show(){
    var r=pick(),p=P[r[0]],box=document.getElementById('qres');
    box.innerHTML='<img src="'+p[1]+'" alt=""><div><b>'+p[0]+'</b><span>'+r[1]+'</span></div>'+
      '<a class="btn" href="'+(r[2]||'/porownanie-vpn#'+r[0])+'">'+(r[3]||'Zobacz szczegóły')+'</a><button type="button" class="again">Zacznij od nowa</button>';
    box.hidden=false;
  }
  q.addEventListener('click',function(e){
    var b=e.target.closest('button');if(!b)return;
    if(b.classList.contains('again')){a={};order.forEach(function(n,i){var s=step(n);s.hidden=i>0;Array.prototype.forEach.call(s.querySelectorAll('button'),function(x){x.removeAttribute('aria-pressed')})});document.getElementById('qres').hidden=true;return}
    var s=b.closest('.qstep');if(!s)return;
    Array.prototype.forEach.call(s.querySelectorAll('button'),function(x){x.setAttribute('aria-pressed',x===b)});
    a[s.dataset.q]=b.dataset.v;
    var i=order.indexOf(s.dataset.q);
    for(var j=i+1;j<order.length;j++){step(order[j]).hidden=true;delete a[order[j]];Array.prototype.forEach.call(step(order[j]).querySelectorAll('button'),function(x){x.removeAttribute('aria-pressed')})}
    document.getElementById('qres').hidden=true;
    if(a.pay==='free'||(a.dev==='many')||i===order.length-1){show()}else{step(order[i+1]).hidden=false}
  });
})();
(function(){
  var els=document.querySelectorAll('section .shead, section .prose > *, .glist li, .prow, .flow, .pb, .hl, .quiz, .devtext, .hsteps li, .tl > div, .provsec, .brief, .faq details');
  if(!('IntersectionObserver' in window)||!els.length)return;
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{rootMargin:'0px 0px -6% 0px'});
  Array.prototype.forEach.call(els,function(el){el.classList.add('rv');io.observe(el)});
  setTimeout(function(){Array.prototype.forEach.call(els,function(el){el.classList.add('in')})},2500);
})();
"""
    s += """
(function(){
  if(!('IntersectionObserver' in window)||(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches))return;
  var els=document.querySelectorAll('.pbprice b, .hld, .featcta > b');
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(!e.isIntersecting)return;io.unobserve(e.target);
    var el=e.target,full=el.textContent,m=full.match(/\\d+(,\\d+)?/);if(!m)return;
    var end=parseFloat(m[0].replace(',','.')),dec=m[1]?m[1].length-1:0,t0=null;
    el.style.fontVariantNumeric='tabular-nums';
    function f(t){if(!t0)t0=t;var k=Math.min(1,(t-t0)/700),v=end*(1-Math.pow(1-k,3));
      el.textContent=k<1?full.replace(m[0],v.toFixed(dec).replace('.',',')):full;if(k<1)requestAnimationFrame(f)}
    requestAnimationFrame(f);
  })},{threshold:.6});
  Array.prototype.forEach.call(els,function(el){io.observe(el)});
})();
"""
    s += """
(function(){
  var sid=(location.pathname.replace(/^[/]+|[/]+$/g,'').replace(/[^a-z0-9-]/gi,'-')||'home').slice(0,60);
  function tag(a){var k=a.href.indexOf('go.expressvpn.com')>=0?'subId1=':'sid=';if(a.href.indexOf(k)<0)a.href+=(a.href.indexOf('?')<0?'?':'&')+k+sid}
  function hit(e){
    var a=e.target&&e.target.closest?e.target.closest('a[data-aff]'):null;
    if(!a)return;tag(a);if(!navigator.sendBeacon)return;
    var r='';try{r=document.referrer?new URL(document.referrer).hostname:''}catch(x){}
    if(r===location.hostname)r='';
    navigator.sendBeacon('/api/click',new Blob([JSON.stringify({p:a.getAttribute('data-aff'),u:location.pathname,r:r})],{type:'application/json'}));
  }
  document.addEventListener('click',hit,true);document.addEventListener('auxclick',hit,true);
  // One visit notice per browser per 30 minutes (new tabs do not count again). Not sent from the owner's devices (open the site once with ?me=1).
  try{
    if(/[?&]me=1/.test(location.search))localStorage.setItem('ps_me','1');
    if(/[?&]me=0/.test(location.search))localStorage.removeItem('ps_me');
    var lv=+localStorage.getItem('ps_v')||0;
    if(navigator.sendBeacon&&!localStorage.getItem('ps_me')&&Date.now()-lv>1800000&&!navigator.webdriver){
      localStorage.setItem('ps_v',String(Date.now()));
      var vr='';try{vr=document.referrer?new URL(document.referrer).hostname:''}catch(x){}
      if(vr===location.hostname)vr='';
      navigator.sendBeacon('/api/visit',new Blob([JSON.stringify({u:location.pathname,r:vr})],{type:'application/json'}));
    }
  }catch(x){}
  // Tell CJ (sid) / Impact (subId1) which page the click came from (sid), so a sale shows its page.
  Array.prototype.forEach.call(document.querySelectorAll('a[data-aff]'),tag);
  // Phone bar: shows after some scrolling, closes for the rest of the visit.
  var sb=document.getElementById('sbar');
  if(sb){
    var off=false;try{off=sessionStorage.getItem('ps_sb')==='1'}catch(x){}
    var upd=function(){var on=!off&&window.scrollY>700;sb.classList.toggle('on',on);document.body.classList.toggle('hasbar',on)};
    window.addEventListener('scroll',upd,{passive:true});upd();
    sb.querySelector('button').addEventListener('click',function(){off=true;try{sessionStorage.setItem('ps_sb','1')}catch(x){}upd()});
  }
})();
"""
    (SITE / "app.js").write_text(s)


def main():
    (SITE / "style.css").write_text((HERE / "fonts.css").read_text() + (HERE / "base.css").read_text() + EXTRA_CSS)
    build_js()
    listed = []
    for path, page in PAGES.items():
        title, desc, body = page[:3]
        kind = page[3] if len(page) > 3 else "page"
        crumbs = page[4] if len(page) > 4 else None
        name = "index.html" if path == "/" else path.strip("/") + ".html"
        (SITE / name).write_text(layout(path, title, desc, with_today(path, body), kind, crumbs).replace("__PARTNERS__", partners()))
        if path not in NOINDEX:
            listed.append((path, title.split(" | ")[0], desc))
    urls = "".join(f"<url><loc>{DOMAIN}{'' if p == '/' else p}</loc><lastmod>{MODIFIED}</lastmod></url>" for p, _, _ in listed)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "PerplexityBot", "Google-Extended", "CCBot"]
    rule = "Allow: /" if INDEXABLE else "Disallow: /"
    robots = f"User-agent: *\n{rule}\nContent-Signal: search=yes, ai-input=yes, ai-train=no\n\n"
    robots += "".join(f"User-agent: {b}\n{rule}\n\n" for b in bots)
    (SITE / "robots.txt").write_text(robots + f"Sitemap: {DOMAIN}/sitemap.xml\n")
    llms = "# Polski Streaming\n\n> Poradniki dla Polaków za granicą i codzienne testy VPN z polskimi serwisami streamingowymi. Wyniki testów pochodzą z własnego bota i mają zrzuty ekranu.\n\n## Strony\n\n"
    llms += "".join(f"- [{t}]({DOMAIN}{'' if p == '/' else p}): {d}\n" for p, t, d in listed)
    llms += f"\n## Dane\n\n- [Wynik ostatniego testu (JSON)]({DOMAIN}/data/latest.json)\n- [Historia testów (JSON)]({DOMAIN}/data/history.json)\n"
    (SITE / "llms.txt").write_text(llms)
    # Bing Webmaster Tools ownership file (the owner's account code, the same one as on his other sites)
    (SITE / "BingSiteAuth.xml").write_text('<?xml version="1.0"?>\n<users>\n\t<user>51BF2F13EF0C496CF9E6659E6E3C6AD0</user>\n</users>\n')
    print("built", len(PAGES), "pages,", len(listed), "in sitemap")


if __name__ == "__main__":
    main()
