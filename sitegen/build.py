"""Build the static site: python3 sitegen/build.py

Writes site/*.html, site/style.css and site/app.js. Test data (site/data/) is written
by the bot and is not touched here.

Content rules:
- No invented test results. A provider or service that the bot did not test says so.
- Provider facts come from the provider's own pages; each has a source and a check date.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent / "site"
DOMAIN = "https://polskistreaming.pl"
UPDATED = "10 listopada 2026"
CHECKED = "10.11.2026"
PUBLISHED = "2026-11-10"
MODIFIED = "2026-11-10"
INDEXABLE = True  # set True when the owner opens the site to search engines
# Pages kept out of search until they have enough substance of their own.
NOINDEX = {"/polsat-box-go-za-granica", "/wyniki-testow", "/prywatnosc"}
_latest = SITE / "data" / "latest.json"
RUN = json.loads(_latest.read_text()) if _latest.exists() else {"providers": [], "services": []}
SVON = [x for x in RUN.get("services", []) if x.get("enabled")]
ST_LABEL = {"ok": "Działa", "blocked": "Nie działa", "unstable": "Niestabilny", "none": "Nie przetestowano"}
ST_ICON = {"ok": '<path d="M20 6 9 17l-5-5"/>', "blocked": '<path d="M18 6 6 18M6 6l12 12"/>',
           "unstable": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>', "none": '<path d="M5 12h14"/>'}


def st(status):
    return (f'<span class="st {status}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ST_ICON[status]}</svg>{ST_LABEL[status]}</span>')


def fmt_dt(iso):
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}, {iso[11:16]}" if iso else "—"


def tested():
    return [p for p in RUN.get("providers", []) if p.get("tested")]


def prov_status_html(pid):
    """Static copy of what app.js renders, so the result is in the HTML that search engines read."""
    p = next((x for x in RUN.get("providers", []) if x["id"] == pid), None)
    if not p or not p.get("tested"):
        return st("none")
    return "".join(f'<span class="pst">{x["name"]}:{st(p["services"].get(x["id"], {}).get("status", "none"))}</span>' for x in SVON)


def svc_rows_html(sid):
    out = ""
    for p in tested():
        r = p["services"].get(sid)
        if not r:
            continue
        plan = f' ({p["plan"]})' if p.get("plan") else ""
        why = f'. {r["reason"]}' if r.get("reason") else ""
        link = f'<a href="/{r["shot"]}" target="_blank" rel="noopener">zrzut ekranu</a>' if r.get("shot") else "<span></span>"
        out += (f'<div class="svcrow"><img src="{LOGOS[p["id"]]}" alt="" width="30" height="30"><b>{p["name"]}{plan}</b>{st(r["status"])}'
                f'<span class="muted">Test: {fmt_dt(r.get("tested_at"))}{why}</span>{link}</div>')
    return out or '<p class="muted" style="padding:14px 0">Tego serwisu jeszcze nie testujemy.</p>'


def last_rows_html():
    out = ""
    for p in tested():
        plan = f' ({p["plan"]})' if p.get("plan") else ""
        out += (f'<div class="lastrow"><img src="{LOGOS[p["id"]]}" alt="" width="30" height="30"><b>{p["name"]}{plan}</b><span>{prov_status_html(p["id"])}</span>'
                f'<span class="muted">Test: {fmt_dt(RUN.get("finished_at"))}</span></div>')
    return out or '<p class="muted">Brak wyniku testu.</p>'

NAV = [("/tvp-vod-za-granica", "TVP VOD"), ("/player-za-granica", "Player"), ("/tvp-sport-za-granica", "TVP Sport"), ("/darmowy-vpn-polska-telewizja", "Darmowy VPN"),
       ("/porownanie-vpn", "Ranking VPN"), ("/jak-testujemy", "Jak testujemy")]


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
<link rel="stylesheet" href="/style.css">
<script>document.documentElement.className="js"</script>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<div class="disc"><div class="wrap">Strona zawiera linki partnerskie. <a href="/jak-testujemy#linki">Jak zarabiamy</a></div></div>
<header class="top"><div class="wrap">
  <a class="logo" href="/"><i aria-hidden="true"></i>Polski Streaming</a>
  <nav class="cnav" aria-label="Główne">{nav}</nav>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">
  <div><b>Polski Streaming</b><br>Niezależne testy VPN z polskimi serwisami streamingowymi.</div>
  <nav><a href="/polsat-box-go-za-granica">Polsat Box Go</a><a href="/wyniki-testow">Test darmowego serwera</a><a href="/o-nas">O nas</a><a href="mailto:kontakt@polskistreaming.pl">kontakt@polskistreaming.pl</a><a href="/jak-testujemy">Jak testujemy</a><a href="/jak-testujemy#linki">Linki partnerskie</a><a href="/prywatnosc">Prywatność</a></nav>
</div></footer>
<script src="/app.js" defer></script>
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
    <div><h2>Wynik ostatniego testu</h2><p id="scope">Darmowy plan Proton VPN, serwer PL-FREE#1 w Warszawie.</p></div>
    <div class="nums">
      <div><b id="s1">—</b><span>serwisów grało w ostatnim teście</span></div>
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
    <div><h2>Darmowych serwerów jest mało. Płatne VPN mają ich więcej.</h2>
      <p>W planie darmowym wielu ludzi korzysta z tych samych serwerów w Polsce. Gdy serwer jest przeciążony albo serwis zablokuje jego adres, trudno przełączyć się na inny. NordVPN podaje 61 serwerów w Polsce i daje 30 dni na zwrot pieniędzy.</p></div>
    <a class="btn big" href="/porownanie-vpn">Zobacz ranking VPN</a>
  </div>
</div></section>"""

HISTORY = """<section class="history" id="historia"><div class="wrap">
  <div class="shead"><h2>Darmowy serwer w ostatnich 30 dniach</h2><p>Darmowy serwer, który działa dziś, jutro może nie działać. Złe dni zostają w historii. Szare pola to dni bez testu.</p></div>
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
  <div class="shead"><h2>Test darmowego serwera: {name}</h2><p>{note} Na razie testujemy tylko darmowy serwer Proton VPN. Darmowe serwery są obciążone i wynik zmienia się z dnia na dzień. Płatnych planów z rankingu jeszcze nie testowaliśmy.</p></div>
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


def errors_box(rows):
    trs = "".join(f"<tr><td>„{m}”</td><td>{w}</td><td>{d}</td></tr>" for m, w, d in rows)
    return ('<h2>Komunikaty błędów i co z nimi zrobić</h2><div class="scrollx keep"><table class="mini3"><thead><tr><th>Komunikat</th><th>Co oznacza</th><th>Co zrobić</th></tr></thead>'
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
                 f'<span><em>Serwer w Polsce</em>{pl}</span><span><em>Zwrot pieniędzy</em>{refund}</span>'
                 f'<span class="pcta"><a class="btn" {plink(pid, url)}>Przejdź do {name}</a>{aff_note(pid)}</span></div>')
    return f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>VPN z serwerem w Polsce</h2><p>{note or 'Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.'}</p></div>
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
    return f'<figure class="sidefig" data-shot="{sid}"></figure><p class="figcap">Zrzut ekranu z ostatniego testu: {name}. To prawdziwy obraz z bota.</p>'


def faq(items):
    rows = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in items)
    return f'<section class="faqs" id="faq"><div class="wrap"><div class="shead"><h2>Częste pytania</h2></div><div class="faq">{rows}</div></div></section>'


LEGAL_Q = ("Czy to jest legalne?", "Używanie VPN jest legalne w Wielkiej Brytanii, Unii Europejskiej i USA. Regulamin serwisu streamingowego może jednak zabraniać omijania blokad regionalnych. Przeczytaj regulamin swojego serwisu.")
FREE_Q = ("Czy darmowy VPN wystarczy?", "Czasem tak. Testujemy darmowy plan Proton VPN z serwerem w Polsce i wynik zmienia się z dnia na dzień. Aktualny wynik jest na górze tej strony. Darmowe serwery są obciążone, więc film może się zacinać.")
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
POINTS = {"surf": (1, 3, 3, 2, 3, 1), "nord": (3, 1, 2, 2, 3, 1), "proton": (1, 3, 2, 2, 3, 1), "cybr": (1, 2, 1, 3, 3, 0), "expr": (1, 1, 3, 2, 3, 0)}
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
    "nord": "https://www.dpbolvw.net/click-101925411-15078184",  # CJ, property "Polski Streaming" (101925411), link "2y Pricing Page"
    "surf": "https://www.dpbolvw.net/click-101925411-15438560",  # CJ advertiser 6282055, text link "Get Surfshark VPN right away" (home page)
    "proton": "https://www.dpbolvw.net/click-101925411-15834536",  # CJ advertiser 5227916, text link "Proton VPN - Special Offer" (Polish offer page)
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
    return ""  # the disclosure is one line under the header, on every page


PROFILE = {
    "proton": dict(tag="Najniższa cena w zestawieniu", badge="", price="7,49 zł", unit="za miesiąc",
                   terms="89,88 zł za pierwsze 12 miesięcy, potem 209,88 zł za rok.",
                   pros=["Najniższa cena w zestawieniu", "10 urządzeń jednocześnie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                   cons=["Niska cena dotyczy pierwszych 12 miesięcy, odnowienie jest droższe"]),
    "nord": dict(tag="Najwięcej serwerów w Polsce", badge="", price="10,99 zł", unit="za miesiąc",
                 terms="296,73 zł za pierwsze 27 miesięcy.",
                 pros=["61 serwerów w Polsce, najwięcej w zestawieniu", "10 urządzeń jednocześnie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Najniższa cena tylko w planie na 27 miesięcy"]),
    "surf": dict(tag="Bez limitu urządzeń", badge="", price="8,99 zł", unit="za miesiąc",
                 terms="242,73 zł za pierwsze 27 miesięcy, plus VAT, jeśli dotyczy.",
                 pros=["Bez limitu urządzeń", "8,99 zł za miesiąc w planie na 27 miesięcy", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Do ceny może dojść VAT"]),
    "expr": dict(tag="Najwięcej urządzeń z limitem: 14", badge="", price="ok. 10,93 zł", unit="za miesiąc (2,49 €)",
                 terms="69,72 € za pierwsze 28 miesięcy, potem 79,95 € za rok. Przeliczenie na złote po kursie NBP z 10.11.2026 (4,3895 zł). Bank może policzyć inaczej.",
                 pros=["Do 14 urządzeń jednocześnie", "Serwer w Warszawie", "Aplikacje na Android TV, Apple TV i Fire TV"],
                 cons=["Cena tylko w euro", "Zwrot w 30 dni tylko dla nowych klientów"]),
    "cybr": dict(tag="Najdłuższy zwrot pieniędzy: 45 dni", badge="", price="ok. 9,61 zł", unit="za miesiąc (2,19 €)",
                 terms="61,32 € za pierwsze 28 miesięcy. Plan na 1 miesiąc: 11,99 €. Przeliczenie na złote po kursie NBP z 10.11.2026 (4,3895 zł). Bank może policzyć inaczej.",
                 pros=["45 dni na zwrot (14 dni w planie miesięcznym)", "7 urządzeń jednocześnie", "Jest plan na jeden miesiąc"],
                 cons=["Jedna lokalizacja w Polsce", "Cena tylko w euro"]),
}
PRICE_SRC = {"proton": ("https://protonvpn.com/pl/pricing", "protonvpn.com/pl/pricing"), "nord": ("https://nordvpn.com/pl/pricing/", "nordvpn.com/pl/pricing"),
             "surf": ("https://surfshark.com/pl/pricing", "surfshark.com/pl/pricing"), "expr": ("https://www.expressvpn.com/pl/pricing", "expressvpn.com/pl/pricing"),
             "cybr": ("https://www.cyberghostvpn.com/pl/buy/cyberghost-vpn-3", "cyberghostvpn.com")}
CHECK = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>'
MINUS = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>'


def featured():
    return f"""<section class="feat"><div class="wrap">
  <div class="featbox">
    <div class="feath"><span class="feattag">Nasz wybór do polskiej telewizji</span>
      <h2><img src="/logos/nord.svg" alt="" width="40" height="40">NordVPN</h2>
      <p>Ma 61 serwerów w Polsce, najwięcej w rankingu. Gdy serwis zablokuje jeden adres, przełączasz się na inny serwer i oglądasz dalej.</p></div>
    <ul class="featl">
      <li>{CHECK}<span>61 serwerów w Polsce</span></li>
      <li>{CHECK}<span>10 urządzeń jednocześnie</span></li>
      <li>{CHECK}<span>Aplikacje na Android TV, Apple TV i Fire TV</span></li>
      <li>{CHECK}<span>30 dni na zwrot pieniędzy</span></li>
    </ul>
    <div class="featcta"><b>10,99 zł</b><span>za miesiąc</span>
      <a class="btn big" {plink("nord", "https://nordvpn.com")}>Przejdź do NordVPN</a>
      <small>296,73 zł za pierwsze 27 miesięcy. Cena z {CHECKED}.</small></div>
  </div>
</div></section>"""


def highlights():
    items = [("nord", "Najwięcej serwerów w Polsce", "61 serwerów"), ("surf", "Bez limitu urządzeń", "8,99 zł za miesiąc"),
             ("cybr", "Najdłuższy zwrot pieniędzy", "45 dni"), ("expr", "Najwięcej urządzeń z limitem", "do 14 naraz"),
             ("proton", "Najniższa cena", "7,49 zł za miesiąc")]
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
      <p class="src">Źródła: <a href="{src}" target="_blank" rel="nofollow noopener">{srcname}</a>, <a href="{ps}" target="_blank" rel="nofollow noopener">{pn}</a>. Sprawdzone {CHECKED}.</p></div>
  </div>""" if full else ""
        out += f"""<article class="pb" id="{pid}">
  <header class="pbh">
    <span class="rank" aria-label="Miejsce {RANK[pid]}">{RANK[pid]}</span>
    <img src="{LOGOS[pid]}" alt="" width="48" height="48">
    <div><h3>{name}{top}{badge}</h3><p>{pr["tag"]}</p></div>
    <div class="pbprice"><b>{pr["price"]}</b><span>{pr["unit"]}</span></div>
    <a class="btn big" {plink(pid, url)}>Przejdź do {name}</a>{aff_note(pid)}
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

LOGOS = {"proton": "/logos/proton.svg", "nord": "/logos/nord.svg", "surf": "/logos/surf.svg", "expr": "/logos/expr.svg", "cybr": "/logos/cyberghost-icon.png"}


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
              band("Polska telewizja za granicą", "Polska telewizja za granicą: jak oglądać i który VPN wybrać",
                   "Poradniki dla Polaków w Wielkiej Brytanii, Niemczech, Holandii i USA. Do tego codzienny test: sprawdzamy, czy film naprawdę gra przez VPN.",
                   '<div class="cta2"><a class="btn big" href="/porownanie-vpn">Zobacz ranking VPN</a><a class="btn big ghost" href="/tvp-vod-za-granica">Jak oglądać TVP VOD</a></div>', image=True)
              + """<section class="svcbar"><div class="wrap">
  <span>Poradniki i testy dla serwisów:</span>
  <a href="/tvp-vod-za-granica"><span class="slogo"><img src="/logos/tvpvod.png" alt="TVP VOD"></span></a>
  <a href="/player-za-granica"><span class="slogo"><img src="/logos/player.svg" alt="Player"></span></a>
  <a href="/tvp-sport-za-granica"><span class="slogo stext">TVP Sport</span></a>
  <a href="/polsat-box-go-za-granica"><span class="slogo"><img src="/logos/polsat.svg" alt="Polsat Box Go"></span></a>
</div></section>"""
              + featured()
              + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Szybki wybór</h2><p>Pięć wyróżnień opartych na faktach ze stron dostawców. Stan na {CHECKED}.</p></div>
  {highlights()}
</div></section>"""
              + """<section class="guides"><div class="wrap">
  <div class="shead"><h2>Poradniki</h2><p>Wybierz serwis, który chcesz oglądać. Każdy poradnik pokazuje legalne opcje bez VPN i sposób z VPN.</p></div>
  <ul class="glist">
    <li><a href="/tvp-vod-za-granica"><b>Jak oglądać TVP VOD za granicą</b><span>Trzy sposoby, wynik codziennego testu i to, na co uważać przy reklamach.</span></a></li>
    <li><a href="/player-za-granica"><b>Jak oglądać Player za granicą</b><span>Darmowe odcinki, pakiet Player International i test z VPN.</span></a></li>
    <li><a href="/tvp-sport-za-granica"><b>Jak oglądać TVP Sport za granicą</b><span>Materiały wideo a transmisje na żywo, wynik testu i liczby z pomiarów.</span></a></li>
    <li><a href="/darmowy-vpn-polska-telewizja"><b>Darmowy VPN do polskiej telewizji</b><span>Jak ustawić darmowy serwer w Polsce i co pokazał nasz test.</span></a></li>
    <li><a href="/polsat-box-go-za-granica"><b>Jak oglądać Polsat Box Go za granicą</b><span>Co działa w Unii Europejskiej i pakiet dla widzów za granicą.</span></a></li>
  </ul>
</div></section>"""
              + f"""<section class="howflow"><div class="wrap narrowpad">
  <div class="shead"><h2>Jak to działa</h2><p>Polskie serwisy sprawdzają adres IP. VPN z serwerem w Polsce daje Ci polski adres, więc serwis traktuje Cię jak widza w kraju.</p></div>
  {flow("Polski serwis", "")}
</div></section>"""
              + QUIZ
              + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Ranking VPN do polskiej telewizji</h2><p>Ranking według punktów za ceny, serwery w Polsce, liczbę urządzeń i zwrot pieniędzy. <a href="/porownanie-vpn#ranking">Jak liczymy punkty</a>.</p></div>
  <div class="pblist compact">{provblocks(False)}</div>
  <p class="after"><a href="/porownanie-vpn">Pełne porównanie z tabelą</a> · Ceny sprawdzone {CHECKED}. To ceny promocyjne i mogą się zmienić.</p>
</div></section>"""
              + DEVICES
              + faq([("Dlaczego polskie serwisy nie działają za granicą?", "Serwisy kupują prawa do filmów i transmisji tylko na Polskę. Sprawdzają Twój adres IP i blokują odtwarzanie spoza kraju."),
                     ("Czy wynik zależy od kraju, w którym mieszkam?", "Nie. Serwis widzi polski adres serwera VPN, a nie Twój adres. Od Twojego kraju zależy tylko prędkość połączenia."),
                     LEGAL_Q, FREE_Q, TV_Q,
                     ("Jak zarabia ta strona?", "Część linków na stronie to linki partnerskie. Dziś partnerami są __PARTNERS__: gdy kupisz przez nasz link, dostajemy prowizję, a Ty płacisz tyle samo. Prowizja nie daje punktów w rankingu i nie zmienia wyników testu.")]))

PAGES["/wyniki-testow"] = ("Test darmowego serwera VPN w Polsce: wyniki | Polski Streaming",
    "Codzienny test darmowego serwera Proton VPN w Polsce z TVP VOD, Playerem i TVP Sport: ostatni wynik, historia 30 dni i zrzuty ekranu.",
    band('<a href="/">Polska telewizja za granicą</a> / Test darmowego serwera', "Test darmowego serwera w Polsce",
         "Każdego ranka bot sprawdza, czy film gra przez darmowy serwer Proton VPN w Polsce. Darmowe serwery są obciążone, więc wynik zmienia się z dnia na dzień.", WHEN)
    + RESULTS + HISTORY + EVIDENCE)

PAGES["/tvp-vod-za-granica"] = ("Jak oglądać TVP VOD za granicą: test VPN | Polski Streaming",
    "TVP VOD za granicą: co działa bez VPN, co jest zablokowane, wynik codziennego testu i komunikaty błędów z rozwiązaniami.",
    band('<a href="/">Polska telewizja za granicą</a> / TVP VOD', "Jak oglądać TVP VOD za granicą",
         "TVP VOD jest darmowy, ale wiele materiałów działa tylko w Polsce. Sprawdzamy to codziennie na programie „Jeden z dziesięciu”.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/tvpvod-test.webp", "vod.tvp.pl", "Zrzut ekranu z naszego testu przez VPN, 10.11.2026. Film gra."))
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
""", "prosec", brief([("Cena", "Darmowy, z reklamami"), ("Konto", "W teście niepotrzebne"), ("Reklamy przed filmem", "Około 2,5 minuty"), ("Nasz test", "Codziennie, „Jeden z dziesięciu”")],
                     [("/porownanie-vpn", "Ranking VPN"), ("/wyniki-testow", "Wyniki testów"), ("/jak-testujemy", "Jak testujemy")]))
    + provstrip()
    + svc_result("tvpvod", "TVP VOD", "Bot włącza najnowszy odcinek programu „Jeden z dziesięciu” i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć TVP VOD przez VPN", "Kolejność ma znaczenie: najpierw VPN, potem strona.", [
        ("Połącz VPN z serwerem w Polsce", "Zrób to przed otwarciem strony. Jeśli strona była już otwarta, odśwież ją po połączeniu."),
        ("Otwórz vod.tvp.pl i kliknij „Akceptuję”", "Bez zgody w okienku prywatności reklamy się nie ładują, a wtedy film nie rusza."),
        ("Wybierz program i kliknij „Odtwórz”", "Przycisk jest pod tytułem programu. Serwis przeniesie Cię do najnowszego odcinka."),
        ("Poczekaj na koniec reklam", "W naszych testach trwały od 156 do 176 sekund. Nie odświeżaj strony, bo reklamy zaczną się od nowa.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Program testowy", "„Jeden z dziesięciu”, najnowszy odcinek"),
        ("Czas reklam przed filmem", "156 do 176 sekund"),
        ("Jakość obrazu", "1920 × 1080 na zwykłym komputerze, 640 × 360 na serwerze testowym"),
        ("Zabezpieczenie DRM", "Nie, w tym programie"),
        ("Logowanie", "Nie było potrzebne"),
        ("Dni pomiarów", "10.11.2026, kilka uruchomień")],
        "To są pomiary naszego bota, a nie dane producenta.")
    + errors_box([
        ("Wykryto wtyczkę adblock", "Reklamy się nie załadowały. Zdarza się, gdy VPN blokuje reklamy na poziomie DNS.", "Wyłącz w aplikacji VPN blokowanie reklam i odśwież stronę."),
        ("Wystąpił problem z materiałem. Spróbuj ponownie za chwilę", "Serwis nie podał filmu. W naszym teście ten sam serwer VPN godzinę wcześniej działał.", "Zmień serwer na inny polski albo spróbuj po kilku minutach."),
        ("Materiał niedostępny w Twoim kraju", "Serwis widzi zagraniczny adres IP.", "Sprawdź, czy VPN jest połączony z Polską, i odśwież stronę.")])
    + '<p class="note">Dwa pierwsze komunikaty widzieliśmy w naszych testach 10.11.2026. Trzeci to zwykła blokada regionalna.</p>',
    "prosec alt", shot("tvpvod", "TVP VOD"))
    + faq([("Czy potrzebuję konta w TVP VOD?", "W naszym teście „Jeden z dziesięciu” grał bez logowania. Część materiałów wymaga konta albo opłaty."),
           ("Czy TVP Sport działa tak samo?", "TVP Sport to osobny serwis (sport.tvp.pl) i testujemy go osobno. Wynik jest na stronie <a href=\"/wyniki-testow\">Wyniki testów</a>."),
           ("Czy mogę oglądać TVP VOD na telewizorze za granicą?", "Tak, jeśli telewizor albo przystawka ma aplikację VPN. TVP VOD ma aplikację na Android TV. Listę aplikacji każdego dostawcy VPN znajdziesz w <a href=\"/porownanie-vpn\">porównaniu</a>."),
           ("Czy to jest legalne?", "Używanie VPN jest legalne w Wielkiej Brytanii, Unii Europejskiej i USA. Regulamin TVP VOD może jednak zabraniać omijania blokad regionalnych, więc przeczytaj go przed użyciem.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/tvp-vod-za-granica", "TVP VOD")])

PAGES["/player-za-granica"] = ("Jak oglądać Player za granicą: test VPN | Polski Streaming",
    "Player za granicą: darmowe odcinki „BEZ OPŁAT”, pakiet Player International, wynik codziennego testu VPN i typowe błędy.",
    band('<a href="/">Polska telewizja za granicą</a> / Player', "Jak oglądać Player za granicą",
         "Player ma darmowe odcinki z reklamami i płatne pakiety. Sprawdzamy codziennie, czy darmowe „Fakty” grają przez VPN.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/player-test.webp", "player.pl", "Zrzut ekranu z naszego testu przez VPN, 10.11.2026. „Fakty” grają."))
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
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + svc_result("player", "Player", "Bot włącza najnowszy darmowy odcinek „Faktów” bez logowania i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć Player przez VPN", "Darmowe odcinki nie wymagają konta.", [
        ("Połącz VPN z serwerem w Polsce", "Player sprawdza adres IP przy starcie filmu, więc VPN musi działać, zanim klikniesz „Oglądaj”."),
        ("Otwórz player.pl i kliknij „Akceptuję”", "Okienko zgody pojawia się przy pierwszej wizycie. Bez niej reklamy się nie włączą."),
        ("Wybierz odcinek z etykietą „BEZ OPŁAT”", "Odcinki bez tej etykiety wymagają płatnego pakietu i logowania."),
        ("Kliknij „Oglądaj” i poczekaj na reklamę", "W naszym teście reklama trwała około 40 sekund, potem ruszył odcinek.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Materiał testowy", "„Fakty”, najnowszy odcinek „BEZ OPŁAT”"),
        ("Czas reklam przed filmem", "Około 40 sekund"),
        ("Jakość obrazu w teście", "640 × 360"),
        ("Zabezpieczenie DRM", "Tak"),
        ("Logowanie", "Nie było potrzebne"),
        ("Dni pomiarów", "10.11.2026, kilka uruchomień")],
        "Jakość 640 × 360 dotyczy przeglądarki bota. Na zwykłym komputerze może być wyższa, tego nie mierzyliśmy.")
    + errors_box([
        ("Wyłącz blokowanie reklam, aby oglądać", "Reklamy się nie załadowały. W naszym teście powodem był serwer DNS dostawcy VPN.", "Wyłącz w aplikacji VPN blokowanie reklam albo zmień DNS i odśwież stronę."),
        ("Czarny ekran po kliknięciu „Oglądaj”", "Film się nie załadował. U nas druga próba po chwili zadziałała.", "Odśwież stronę. Jeśli to nie pomoże, zmień serwer VPN na inny polski."),
        ("Przekierowanie na stronę logowania", "Wybrany materiał jest w płatnym pakiecie.", "Wybierz odcinek „BEZ OPŁAT” albo zaloguj się na konto z pakietem.")])
    + '<p class="note">Testujemy darmową część Playera. Płatnych pakietów i Player International jeszcze nie testujemy.</p>',
    "prosec alt", shot("player", "Player"))
    + faq([("Czym różni się Player International od VPN?", "Player International to płatny pakiet od Playera, legalny i bez VPN, ale z ograniczoną ofertą. Z VPN widzisz polską wersję serwisu, w tym darmowe odcinki."),
           ("Dlaczego darmowy odcinek zniknął?", "Darmowe odcinki są dostępne przez kilka dni. Przy „Faktach” serwis pokazuje etykietę z dniem, w którym odcinek zniknie."),
           ("Czy potrzebuję konta?", "Do odcinków „BEZ OPŁAT” nie. W naszym teście „Fakty” grały bez logowania."),
           ("Czy to jest legalne?", "Używanie VPN jest legalne w Wielkiej Brytanii, Unii Europejskiej i USA. Regulamin Playera może zabraniać omijania blokad regionalnych. Oficjalną drogą jest Player International.")]),
    "article", [("/", "Polska telewizja za granicą"), ("/player-za-granica", "Player")])

PAGES["/tvp-sport-za-granica"] = ("Jak oglądać TVP Sport za granicą: test VPN | Polski Streaming",
    "TVP Sport za granicą: czym różnią się materiały wideo od transmisji na żywo, wynik codziennego testu VPN i liczby z naszych pomiarów.",
    band('<a href="/">Polska telewizja za granicą</a> / TVP Sport', "Jak oglądać TVP Sport za granicą",
         "TVP Sport jest darmowy i działa w przeglądarce. Za granicą część materiałów jest zablokowana. Sprawdzamy codziennie, czy wideo gra przez VPN.",
         f'<div class="when mono">{BYLINE}<span>Aktualizacja: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>',
         figure=frame("/img/tvpsport-test.webp", "sport.tvp.pl", "Zrzut ekranu z naszego testu przez VPN, 10.11.2026. Wideo gra."))
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
<p>Krótkie materiały wideo często działają także za granicą. Otwórz materiał i sprawdź, czy rusza.</p>
<h3>2. VPN z serwerem w Polsce</h3>
<!--flow:tvpsport-->
<p>Gdy materiał jest zablokowany, polski adres IP z VPN zwykle wystarcza. W naszym teście wideo ruszyło za pierwszym razem także wtedy, gdy TVP VOD przez ten sam serwer nie działał.</p>
<h3>3. Transmisje na żywo</h3>
<p>Nie mamy jeszcze wyniku testu dla transmisji na żywo. Jeśli zależy Ci na konkretnym meczu, sprawdź połączenie wcześniej na innej transmisji i miej w zapasie drugi polski serwer.</p>
""", "prosec", brief([("Cena", "Darmowy, z reklamami"), ("Konto", "W teście niepotrzebne"), ("Reklamy przed wideo", "Około 50 sekund"), ("Nasz test", "Codziennie, najnowsze wideo")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/wyniki-testow", "Wyniki testów"), ("/porownanie-vpn", "Porównanie VPN")]))
    + provstrip("Pięciu dostawców z serwerem w Polsce, w kolejności z naszego rankingu.")
    + svc_result("tvpsport", "TVP Sport", "Bot otwiera dział „Wideo”, wybiera najnowszy materiał dłuższy niż 80 sekund i sprawdza, czy gra 60 sekund.")
    + steps("Jak włączyć wideo z TVP Sport przez VPN", "Odtwarzacz jest na stronie artykułu, pod tytułem.", [
        ("Połącz VPN z serwerem w Polsce", "Najlepiej przed otwarciem strony."),
        ("Otwórz sport.tvp.pl i kliknij „Akceptuję”", "Okienko zgody zasłania stronę przy pierwszej wizycie."),
        ("Wejdź w dział „Wideo” i wybierz materiał", "Materiały wideo mają w tytule dopisek [WIDEO]."),
        ("Kliknij przycisk odtwarzania na obrazie", "Najpierw lecą reklamy. W naszych testach trwały od 46 do 55 sekund.")])
    + prose(facts_box("Liczby z naszego testu", [
        ("Materiał testowy", "Najnowsze wideo z działu „Wideo”"),
        ("Czas reklam przed wideo", "46 do 55 sekund"),
        ("Jakość obrazu", "1920 × 1080"),
        ("Zabezpieczenie DRM", "Nie"),
        ("Logowanie", "Nie było potrzebne"),
        ("Dni pomiarów", "10.11.2026, dwa uruchomienia")],
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
  <div class="svc lastbox" data-last>{last_rows_html()}</div>
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
""", "prosec", brief([("Konto", "Wymagane"), ("Darmowe treści bez konta", "Nie znaleźliśmy"), ("W Unii Europejskiej", "Działa na czasowym wyjeździe"), ("Nasz test", "Jeszcze nie testujemy")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/player-za-granica", "Player za granicą"), ("/porownanie-vpn", "Porównanie VPN")])),
    "article", [("/", "Polska telewizja za granicą"), ("/polsat-box-go-za-granica", "Polsat Box Go")])

PAGES["/porownanie-vpn"] = ("Ranking VPN do polskiej telewizji 2026 | Polski Streaming",
    "Ranking pięciu VPN z serwerem w Polsce: ceny w złotówkach, zwrot pieniędzy, liczba urządzeń, zalety i wady. Jawne zasady punktacji.",
    band('<a href="/">Polska telewizja za granicą</a> / Porównanie VPN', "Ranking VPN do polskiej telewizji",
         "Pięciu dostawców, te same pytania do każdego: ile kosztuje, czy ma serwer w Polsce, ile daje czasu na zwrot i czy sprawdziliśmy go w teście.",
         f'<div class="when mono">{BYLINE}<span>Ceny i dane sprawdzone: <b>{CHECKED}</b></span><span>Ostatni test: <b id="last">{LAST}</b></span></div>', image="shield")
    + featured()
    + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Szybki wybór</h2><p>Pięć wyróżnień opartych na faktach ze stron dostawców.</p></div>
  {highlights()}
</div></section>"""
    + QUIZ
    + f"""<section class="guides"><div class="wrap">
  <div class="shead"><h2>Ranking VPN do polskiej telewizji</h2><p>Kolejność wynika z punktów za fakty ze stron dostawców: serwery w Polsce, cena, urządzenia, zwrot, aplikacje i waluta. <a href="#ranking">Zasady punktacji</a> są niżej.</p></div>
  <div class="pblist">{provblocks()}</div>
  <p class="after">Ceny odczytaliśmy ze stron dostawców {CHECKED}. To ceny promocyjne za pierwszy okres i mogą się zmienić. Po pierwszym okresie plan odnawia się zwykle drożej.</p>
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
<p class="note"><b>To ranking na podstawie danych producentów, a nie testów.</b> Własny test mamy dziś dla jednego dostawcy. Wyniki testu są na stronie <a href="/wyniki-testow">Wyniki testów</a>. Nie wliczamy ich do punktów, dopóki nie przetestujemy wszystkich pięciu dostawców.</p>
""", "prosec", brief([("Testujemy dziś", "Proton VPN, plan darmowy"), ("Serwisy w teście", "TVP VOD, Player, TVP Sport"), ("Ceny", "Ze stron dostawców, z datą")],
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
<p>Testujemy darmowe serwisy: TVP VOD, Player i TVP Sport. Płatnych serwisów jeszcze nie. Z dostawców VPN testujemy na razie Proton VPN w planie darmowym. Pozostałych dodamy, gdy będziemy mieć konta testowe. Do tego czasu ich wynik to „Nie przetestowano”.</p>

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
  <li><b>10.11.2026:</b> pierwszy test (Proton VPN, TVP VOD, Player).</li>
  <li><b>10.11.2026:</b> dodany TVP Sport. Bot wybiera codziennie najnowszy materiał wideo z sport.tvp.pl.</li>
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
    "Polski Streaming nie używa plików cookie, analityki ani reklam śledzących.",
    band('<a href="/">Polska telewizja za granicą</a> / Prywatność', "Prywatność",
         "Krótko: nie śledzimy Cię.")
    + prose("""
<h2>Czego nie robimy</h2>
<ul>
  <li>Nie ustawiamy plików cookie.</li>
  <li>Nie używamy analityki ani pikseli reklamowych.</li>
  <li>Nie ładujemy czcionek, ikon ani skryptów z cudzych serwerów. Wszystko jest na naszej domenie.</li>
</ul>
<h2>Co widzi serwer</h2>
<p>Strona działa na serwerach firmy Vercel. Jak każdy serwer WWW zapisuje ona techniczne logi: adres IP, czas i adres otwartej strony. Nie łączymy tych danych z niczym innym.</p>
<h2>Linki do dostawców</h2>
<p>Przyciski „Strona dostawcy” prowadzą na strony firm VPN. Po kliknięciu obowiązuje ich polityka prywatności. Część z nich to linki partnerskie. Link partnerski prowadzi przez serwer sieci afiliacyjnej (CJ), która zapisuje kliknięcie, żeby przypisać zakup. My nie widzimy, kto kliknął.</p>
""", "prosec"),
    "page", [("/", "Polska telewizja za granicą"), ("/prywatnosc", "Prywatność")])

EXTRA_CSS = """
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
"""


def build_js():
    s = (HERE / "app.src.js").read_text()

    def rep(a, b):
        nonlocal s
        assert a in s, a[:70]
        s = s.replace(a, b)

    rep("var $=function(id){return document.getElementById(id)};",
        "var DUMMY=document.createElement('div');var $=function(id){return document.getElementById(id)||DUMMY};\n"
        "  var LINK={proton:'https://www.dpbolvw.net/click-101925411-15834536',nord:'https://www.dpbolvw.net/click-101925411-15078184',surf:'https://www.dpbolvw.net/click-101925411-15438560',expr:'https://www.expressvpn.com',cybr:'https://www.cyberghostvpn.com'};")
    rep("var PRICE={proton:['0 zł','plan darmowy']};", "var PRICE={proton:['darmowy','0 zł']};")
    rep("'<td><button class=\"btn\" type=\"button\" data-cta aria-label=\"Sprawdź ofertę '+esc(p.name)+'\">Sprawdź ofertę</button></td></tr>'",
        "'<td><a class=\"btn\" href=\"'+LINK[p.id]+'\" target=\"_blank\" rel=\"nofollow noopener\">Strona dostawcy</a></td></tr>'")
    rep("'<button class=\"btn\" type=\"button\" data-cta>Sprawdź ofertę '+esc(p.name)+'</button></details>'",
        "'<a class=\"btn\" href=\"'+LINK[p.id]+'\" target=\"_blank\" rel=\"nofollow noopener\">Strona '+esc(p.name)+'</a></details>'")
    rep("<th>Cena za miesiąc</th><th>Oferta partnera</th>", "<th>Plan w teście</th><th>Oferta</th>")
    rep("<div><span>Cena za miesiąc</span>", "<div><span>Plan w teście</span>")
    rep("Płatnych serwisów (Polsat Box Go, Canal+ Online) jeszcze nie testujemy.'", "Płatnych serwisów jeszcze nie testujemy.'")
    rep("$('scope').textContent='Testujemy na razie '+tested.length+' z '+RUN.providers.length+' dostawców i '+SVON.length+' darmowe serwisy.", "$('scope').textContent='Darmowy plan Proton VPN, serwer PL-FREE#1 w Warszawie. Testujemy '+SVON.length+' darmowe serwisy.")
    rep("$('s1').textContent=tested.filter(function(p){return stat(p,'tvpvod')==='ok'}).length+'/'+tested.length;", "$('s1').textContent=(tested[0]?works(tested[0]):0)+'/'+SVON.length;var sb=document.querySelector('.sortbar');if(sb&&tested.length<2)sb.style.display='none';")
    rep("data=sorted(),tested=RUN.providers.filter(function(p){return p.tested});", "tested=RUN.providers.filter(function(p){return p.tested}),data=sorted().filter(function(p){return p.tested});")
    rep("    RUN.providers.forEach(function(p){\n      var o=0,t=0,cells='';", "    RUN.providers.filter(function(p){return p.tested}).forEach(function(p){\n      var o=0,t=0,cells='';")
    rep("$('hprov').innerHTML=RUN.providers.map(", "$('hprov').innerHTML=RUN.providers.filter(function(p){return p.tested}).map(")
    rep("    render();\n  }",
        "    all('[data-svc]',function(el){var sid=el.dataset.svc,h='';RUN.providers.filter(function(p){return p.tested}).forEach(function(p){var r=p.services[sid];if(!r)return;"
        "h+='<div class=\"svcrow\">'+logo(p.id)+'<b>'+esc(p.name)+(p.plan?' ('+esc(p.plan)+')':'')+'</b>'+st(r.status)+'<span class=\"muted\">Test: '+fmtDT(r.tested_at)+(r.reason?'. '+esc(r.reason):'')+'</span>'"
        "+(r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\">zrzut ekranu</a>':'<span></span>')+'</div>'});"
        "el.innerHTML=h||'<p class=\"muted\" style=\"padding:14px 0\">Tego serwisu jeszcze nie testujemy.</p>'});\n"
        "    all('[data-prov-status]',function(el){var p=RUN.providers.filter(function(x){return x.id===el.dataset.provStatus})[0];"
        "el.innerHTML=p&&p.tested?SVON.map(function(s){return '<span class=\"pst\">'+esc(s.name)+':'+st(stat(p,s.id))+'</span>'}).join(''):st('none')});\n"
        "    all('[data-last]',function(el){var h='';RUN.providers.filter(function(p){return p.tested}).forEach(function(p){"
        "h+='<div class=\"lastrow\">'+logo(p.id)+'<b>'+esc(p.name)+(p.plan?' ('+esc(p.plan)+')':'')+'</b><span>'+SVON.map(function(s){return '<span class=\"pst\">'+esc(s.name)+':'+st(stat(p,s.id))+'</span>'}).join('')+'</span><span class=\"muted\">Test: '+fmtDT(RUN.finished_at)+'</span></div>'});el.innerHTML=h});\n"
        "    all('[data-shot]',function(el){var p=best(),r=p&&p.services&&p.services[el.dataset.shot];el.innerHTML=r&&r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"/'+esc(r.shot)+'\" alt=\"Zrzut ekranu z testu\" loading=\"lazy\" width=\"1440\" height=\"900\"></a>':''});\n"
        "    render();\n  }")
    rep("get('data/latest.json'),get('data/history.json')", "get('/data/latest.json'),get('/data/history.json')")
    rep("proton:'https://cdn.simpleicons.org/protonvpn',nord:'https://cdn.simpleicons.org/nordvpn',surf:'https://cdn.simpleicons.org/surfshark',expr:'https://cdn.simpleicons.org/expressvpn'",
        "proton:'/logos/proton.svg',nord:'/logos/nord.svg',surf:'/logos/surf.svg',expr:'/logos/expr.svg'")
    rep("https://flagcdn.com/", "/flags/")
    for old in ["'logos/tvpvod.png'", "'logos/player.svg'", "'logos/polsat.svg'", "'logos/canal.svg'", "'logos/cyberghost-icon.png'"]:
        rep(old, "'/" + old[1:])
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
    if(a.prio==='price')return ['proton','Najniższa cena w zestawieniu: 7,49 zł za miesiąc przez pierwsze 12 miesięcy.'];
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
        (SITE / name).write_text(layout(path, title, desc, body, kind, crumbs).replace("__PARTNERS__", partners()))
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
