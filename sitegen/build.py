"""Build the static site: python3 sitegen/build.py

Writes site/*.html, site/style.css and site/app.js. Test data (site/data/) is written
by the bot and is not touched here.

Content rules:
- No invented test results. A provider or service that the bot did not test says so.
- Provider facts come from the provider's own pages; each has a source and a check date.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent / "site"
DOMAIN = "https://polskistreaming.pl"
UPDATED = "10 listopada 2026"
CHECKED = "10.11.2026"
INDEXABLE = False  # set True when the owner opens the site to search engines

NAV = [("/tvp-vod-za-granica", "TVP VOD"), ("/player-za-granica", "Player"), ("/polsat-box-go-za-granica", "Polsat Box Go"),
       ("/porownanie-vpn", "Porównanie VPN"), ("/jak-testujemy", "Jak testujemy")]


def layout(path, title, desc, body):
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == path else "", t) for h, t in NAV)
    robots = "" if INDEXABLE else '<meta name="robots" content="noindex, nofollow">\n'
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}{'' if path == '/' else path}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div class="mock"><div class="wrap">Strona w budowie. Wyniki testów i zrzuty ekranu są prawdziwe. Linki do dostawców nie są jeszcze linkami partnerskimi.</div></div>
<header class="top"><div class="wrap">
  <a class="logo" href="/"><i aria-hidden="true"></i>Polski Streaming <span>Monitor</span></a>
  <nav class="cnav" aria-label="Główne">{nav}</nav>
</div></header>
{body}
<footer><div class="wrap">
  <div><b>Polski Streaming Monitor</b><br>Niezależne testy VPN z polskimi serwisami streamingowymi.</div>
  <nav><a href="/jak-testujemy">Jak testujemy</a><a href="/porownanie-vpn">Porównanie VPN</a><a href="/jak-testujemy#linki">Linki partnerskie</a></nav>
</div></footer>
<script src="/app.js" defer></script>
</body>
</html>
"""


def band(crumb, h1, lead, extra="", image=False):
    img = ('<img class="hero" src="/hero-uk.webp" srcset="/hero-uk-sm.webp 887w, /hero-uk.webp 1774w" sizes="(max-width:820px) 100vw, 780px" '
           'width="1774" height="887" alt="Ilustracja: połączenie z zagranicy do Polski">') if image else ""
    credit = '<div class="credit">Ilustracja. To nie jest zrzut ekranu z testu.</div>' if image else ""
    return f"""<div class="open{'' if image else ' solo'}"><div class="wrap">
  <div class="otext">
    <div class="crumb">{crumb}</div>
    <h1>{h1}</h1>
    <p>{lead}</p>
    {extra}
  </div>
  {img}
</div>{credit}</div>"""


WHEN = """<div class="when mono">
      <span>Ostatni test: <b id="last">—</b></span>
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
    <div>Kolejność zależy tylko od wyniku testu. <a href="/jak-testujemy">Jak testujemy</a></div>
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


def svc_result(sid, name):
    return f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Wynik ostatniego testu: {name}</h2><p>Bot sprawdza to każdego ranka. Wynik poniżej pochodzi z ostatniego testu, a nie z opisu producenta.</p></div>
  <div class="svc" data-svc="{sid}"><p class="muted">Ładowanie wyniku testu…</p></div>
  <p class="after"><a href="/#historia">Historia 30 dni</a> · <a href="/#dowod">Wszystkie zrzuty ekranu</a> · <a href="/jak-testujemy">Jak testujemy</a></p>
</div></section>"""


def steps(service):
    return f"""<section class="howto"><div class="wrap">
  <div class="side"><h2>Jak włączyć {service} przez VPN</h2><p>Cztery kroki. Zajmuje to około 5 minut.</p></div>
  <ol class="hsteps">
    <li><span class="n">01</span><h3>Wybierz VPN z polskim serwerem</h3><p>Zobacz <a href="/porownanie-vpn">porównanie VPN</a> i wynik ostatniego testu.</p></li>
    <li><span class="n">02</span><h3>Zainstaluj aplikację</h3><p>Na komputerze, telefonie albo telewizorze z Android TV lub Fire TV.</p></li>
    <li><span class="n">03</span><h3>Połącz się z serwerem w Polsce</h3><p>Urządzenie dostaje polski adres IP. Serwis widzi ten adres, a nie Twój.</p></li>
    <li><span class="n">04</span><h3>Otwórz {service}</h3><p>Nie działa? Zmień serwer na inny polski, wyłącz blokowanie reklam i odśwież stronę.</p></li>
  </ol>
</div></section>"""


def prose(html, cls="faqs", aside=""):
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

# ---------------------------------------------------------------- pages

PAGES = {}

PAGES["/"] = ("Polska telewizja za granicą: który VPN działa? | Polski Streaming Monitor",
              "Codzienne testy VPN z TVP VOD, Playerem i TVP Sport. Prawdziwe wyniki i zrzuty ekranu dla Polaków za granicą.",
              band("Polska telewizja za granicą", "Polska telewizja za granicą: który VPN działa?",
                   "Poradniki dla Polaków za granicą i codzienny test: bot łączy się przez VPN z serwerem w Polsce i sprawdza, czy film naprawdę gra.",
                   WHEN, image=True)
              + RESULTS
              + """<section class="guides"><div class="wrap">
  <div class="shead"><h2>Poradniki</h2></div>
  <ul class="glist">
    <li><a href="/tvp-vod-za-granica"><b>Jak oglądać TVP VOD za granicą</b><span>Trzy sposoby, wynik codziennego testu i to, na co uważać przy reklamach.</span></a></li>
    <li><a href="/player-za-granica"><b>Jak oglądać Player za granicą</b><span>Darmowa część Playera, pakiet Player International i test z VPN.</span></a></li>
    <li><a href="/polsat-box-go-za-granica"><b>Jak oglądać Polsat Box Go za granicą</b><span>Co działa w Unii Europejskiej, pakiet Polonia i czego jeszcze nie testujemy.</span></a></li>
    <li><a href="/porownanie-vpn"><b>Porównanie VPN z serwerem w Polsce</b><span>Pięciu dostawców: fakty ze stron producentów i nasze wyniki testów.</span></a></li>
  </ul>
</div></section>"""
              + HISTORY + EVIDENCE
              + faq([("Dlaczego polskie serwisy nie działają za granicą?", "Serwisy kupują prawa do filmów i transmisji tylko na Polskę. Sprawdzają Twój adres IP i blokują odtwarzanie spoza kraju."),
                     ("Dlaczego wynik zmienia się z dnia na dzień?", "Serwisy blokują adresy serwerów VPN, a dostawcy VPN dodają nowe. Do tego dochodzi obciążenie serwera. Dlatego testujemy codziennie i pokazujemy historię."),
                     ("Czy wynik zależy od kraju, w którym mieszkam?", "Nie. Serwis widzi polski adres serwera VPN, a nie Twój adres. Od Twojego kraju zależy tylko prędkość połączenia."),
                     LEGAL_Q, FREE_Q,
                     ("Jak zarabia ta strona?", "Strona będzie zarabiać na linkach partnerskich do dostawców VPN. Dziś linki nie są jeszcze partnerskie. Prowizja nie zmienia wyników testu ani kolejności w tabeli.")]))

PAGES["/tvp-vod-za-granica"] = ("Jak oglądać TVP VOD za granicą (test z " + CHECKED + ") | Polski Streaming Monitor",
    "TVP VOD za granicą: trzy sposoby, wynik codziennego testu VPN i zrzut ekranu jako dowód.",
    band('<a href="/">Polska telewizja za granicą</a> / TVP VOD', "Jak oglądać TVP VOD za granicą",
         "TVP VOD jest darmowy, ale wiele materiałów działa tylko w Polsce. Poniżej są trzy sposoby i wynik naszego codziennego testu.",
         f'<div class="when mono"><span>Aktualizacja poradnika: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">—</b></span></div>')
    + svc_result("tvpvod", "TVP VOD")
    + prose("""
<h2>Dlaczego TVP VOD nie działa za granicą</h2>
<p>TVP kupuje prawa do wielu filmów, seriali i transmisji tylko na terytorium Polski. Serwis sprawdza adres IP urządzenia. Gdy adres jest zagraniczny, część materiałów się nie włącza.</p>
<p>Nie wszystko jest zablokowane. Własne produkcje TVP często działają także za granicą. TVP ma w menu serwisu stronę <a href="https://vod.tvp.pl/tvp-vod-za-granica" target="_blank" rel="noopener">TVP VOD za granicą</a>, na której można sprawdzić dostępność.</p>

<h2>Trzy sposoby</h2>
<h3>1. Sprawdź, czy materiał działa bez VPN</h3>
<p>Otwórz program na vod.tvp.pl. Jeśli gra, nie potrzebujesz niczego więcej. To dotyczy głównie produkcji własnych TVP.</p>
<h3>2. W Unii Europejskiej: przenośność płatnych usług</h3>
<p>Unijne rozporządzenie o przenośności (2017/1128) daje dostęp do <b>płatnych</b> subskrypcji podczas czasowego pobytu w innym kraju UE. Dla darmowych serwisów to nie jest obowiązek. Po Brexicie ta zasada nie obejmuje Wielkiej Brytanii (<a href="https://www.gov.uk/guidance/cross-border-portability-of-online-content-services-after-the-transition-period" target="_blank" rel="noopener">źródło: gov.uk</a>).</p>
<h3>3. VPN z serwerem w Polsce</h3>
<p>VPN daje Twojemu urządzeniu polski adres IP. Serwis widzi wtedy użytkownika z Polski. To, czy film naprawdę ruszy, zależy od dostawcy VPN i od dnia. Dlatego sprawdzamy to codziennie.</p>
""", "prosec", brief([("Cena", "Darmowy, z reklamami"), ("Konto", "Nie zawsze potrzebne"), ("Blokada", "Po adresie IP, zależy od materiału"), ("Nasz test", "Codziennie, program „Jeden z dziesięciu”")],
                     [("/porownanie-vpn", "Porównanie VPN"), ("/jak-testujemy", "Jak testujemy")]))
    + steps("TVP VOD")
    + prose(f"""
<h2>Co zauważyliśmy w testach</h2>
<ul>
  <li><b>Reklamy przed programem.</b> W naszych testach TVP VOD pokazywał około 2,5 minuty reklam, zanim ruszył program. Poczekaj, zanim uznasz, że coś nie działa.</li>
  <li><b>Komunikat o adblocku.</b> Gdy bot używał serwera DNS dostawcy VPN (Proton VPN, {CHECKED}), TVP VOD pokazał komunikat „Wykryto wtyczkę adblock”. Po zmianie DNS na neutralny (1.1.1.1) film ruszył. Jeśli widzisz ten komunikat, wyłącz w aplikacji VPN blokowanie reklam.</li>
  <li><b>Błąd „Wystąpił problem z materiałem”.</b> Tego samego dnia ten sam serwer raz działał, a raz TVP VOD pokazał ten błąd dwa razy z rzędu. Zmiana serwera na inny polski albo ponowna próba po kilku minutach często pomaga.</li>
</ul>
<p class="note">To są obserwacje z naszych testów, nie obietnica. Aktualny wynik jest zawsze na górze tej strony.</p>
""", "prosec alt", shot("tvpvod", "TVP VOD"))
    + faq([LEGAL_Q, FREE_Q, TV_Q,
           ("Czy potrzebuję konta w TVP VOD?", "W naszym teście program „Jeden z dziesięciu” grał bez logowania. Część materiałów wymaga konta albo opłaty.")]))

PAGES["/player-za-granica"] = ("Jak oglądać Player za granicą (test z " + CHECKED + ") | Polski Streaming Monitor",
    "Player za granicą: darmowa część serwisu, pakiet Player International i wynik codziennego testu VPN.",
    band('<a href="/">Polska telewizja za granicą</a> / Player', "Jak oglądać Player za granicą",
         "Player ma darmowe materiały z reklamami i płatne pakiety. Za granicą część z nich jest zablokowana. Poniżej są sposoby i wynik naszego testu.",
         f'<div class="when mono"><span>Aktualizacja poradnika: <b>{UPDATED}</b></span><span>Ostatni test: <b id="last">—</b></span></div>')
    + svc_result("player", "Player")
    + prose("""
<h2>Co wybrać</h2>
<h3>1. Player International: oficjalna opcja</h3>
<p>Player ma własny pakiet dla widzów za granicą. Serwis opisuje go tak: „dostęp do twoich ulubionych kanałów TVN i VOD z zagranicy”. To legalna droga bez VPN. Zakres i cenę sprawdź na stronie <a href="https://player.pl/playerplus/player-international" target="_blank" rel="noopener">Player International</a>, bo nie obejmuje całej oferty.</p>
<h3>2. W Unii Europejskiej: przenośność płatnych pakietów</h3>
<p>Jeśli masz płatny pakiet i jesteś czasowo w innym kraju UE, unijne przepisy o przenośności (2017/1128) dają Ci dostęp do Twojej subskrypcji. Nie dotyczy to Wielkiej Brytanii.</p>
<h3>3. VPN z serwerem w Polsce</h3>
<p>Z polskim adresem IP Player zachowuje się tak jak w Polsce. Testujemy darmowy materiał: bot włącza „Fakty” bez logowania i sprawdza, czy film gra 60 sekund.</p>
""", "prosec", brief([("Darmowa część", "Tak, z reklamami"), ("Opcja oficjalna", "Player International"), ("Zabezpieczenie", "DRM, działa w Chrome"), ("Nasz test", "Codziennie, program „Fakty”")],
                     [("/porownanie-vpn", "Porównanie VPN"), ("/jak-testujemy", "Jak testujemy")]))
    + steps("Player")
    + prose(f"""
<h2>Co zauważyliśmy w testach</h2>
<ul>
  <li><b>Materiały są zabezpieczone (DRM).</b> Player szyfruje wideo. W zwykłej przeglądarce Chrome działa to bez dodatków, także przez VPN.</li>
  <li><b>Blokowanie reklam zatrzymuje film.</b> Gdy reklamy się nie ładują, Player pokazuje „Wyłącz blokowanie reklam, aby oglądać”. Zdarzyło się to z serwerem DNS dostawcy VPN (Proton VPN, {CHECKED}). Wyłącz w aplikacji VPN blokowanie reklam.</li>
  <li><b>Czarny ekran.</b> W jednym z testów ekran odtwarzacza został czarny, a druga próba po chwili zadziałała. Taki wynik oznaczamy jako „Niestabilny”.</li>
</ul>
<p class="note">Testujemy darmową część Playera. Płatnych pakietów i Player International jeszcze nie testujemy.</p>
""", "prosec alt", shot("player", "Player"))
    + faq([LEGAL_Q, FREE_Q, TV_Q]))

PAGES["/polsat-box-go-za-granica"] = ("Jak oglądać Polsat Box Go za granicą | Polski Streaming Monitor",
    "Polsat Box Go za granicą: co działa w UE, pakiet Polonia i dlaczego jeszcze nie testujemy tego serwisu.",
    band('<a href="/">Polska telewizja za granicą</a> / Polsat Box Go', "Jak oglądać Polsat Box Go za granicą",
         "Polsat Box Go wymaga konta, a większość treści jest płatna. Tego serwisu jeszcze nie testujemy, więc na tej stronie są tylko sprawdzone fakty i źródła.",
         f'<div class="when mono"><span>Aktualizacja poradnika: <b>{UPDATED}</b></span></div>')
    + prose(f"""
<p class="note"><b>Nie testujemy jeszcze Polsat Box Go.</b> Do testu potrzebny jest płatny pakiet. Nie publikujemy wyników, których sami nie zmierzyliśmy. Gdy zaczniemy testy, wynik pojawi się na tej stronie.</p>

<h2>Co sprawdziliśmy sami ({CHECKED})</h2>
<ul>
  <li>Adres polsatgo.pl przekierowuje teraz do polsatboxgo.pl. Osobnego darmowego serwisu Polsat Go już tam nie ma.</li>
  <li>Próba odtworzenia serialu bez konta kończy się przekierowaniem na stronę logowania.</li>
</ul>

<h2>Sposoby</h2>
<h3>1. W Unii Europejskiej: przenośność</h3>
<p>Jeśli masz płatny pakiet i jesteś czasowo w innym kraju UE, przepisy o przenośności (2017/1128) dają Ci dostęp do Twojej subskrypcji. Kluczowe jest słowo „czasowo”: dotyczy to wyjazdu, a nie stałego mieszkania za granicą. Zasada nie obejmuje Wielkiej Brytanii ani USA.</p>
<h3>2. Pakiet dla widzów za granicą</h3>
<p>Według serwisów <a href="https://bezprawnik.pl/jak-ogladac-tv-za-granica/" target="_blank" rel="noopener">Bezprawnik</a> i <a href="https://android.com.pl/sponsorowany/436490-polsat-box-go-co-wybrac-roznice-grupa-plus/" target="_blank" rel="noopener">Android.com.pl</a> Polsat Box Go ma pakiet „Polonia” dla osób przebywających poza Polską, z treściami, na które licencja pozwala za granicą. Nie potwierdziliśmy tego w oficjalnym cenniku. Aktualną ofertę sprawdź na <a href="https://polsatboxgo.pl/pakiety" target="_blank" rel="noopener">polsatboxgo.pl/pakiety</a>.</p>
<h3>3. VPN z serwerem w Polsce</h3>
<p>Inne serwisy opisują VPN jako sposób na Polsat Box Go. My tego nie sprawdziliśmy, więc nie podajemy, który VPN działa. Zobacz <a href="/porownanie-vpn">porównanie VPN</a> i wyniki dla serwisów, które testujemy: <a href="/tvp-vod-za-granica">TVP VOD</a> i <a href="/player-za-granica">Player</a>.</p>
""", "prosec", brief([("Konto", "Wymagane"), ("Darmowe treści bez konta", "Nie znaleźliśmy"), ("W Unii Europejskiej", "Przenośność płatnych pakietów"), ("Nasz test", "Jeszcze nie testujemy")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/player-za-granica", "Player za granicą"), ("/porownanie-vpn", "Porównanie VPN")]))
    + faq([LEGAL_Q, TV_Q,
           ("Kiedy zaczniecie testować Polsat Box Go?", "Gdy strona będzie miała budżet na płatny pakiet. Do tego czasu ta strona zawiera tylko fakty ze źródeł.")]))

FACTS = [
    ("proton", "Proton VPN", "https://protonvpn.com", "Tak. Polska jest też w planie darmowym.", "30 dni", "Nie podano na sprawdzonej stronie", "Android TV, Apple TV, Fire TV",
     "https://protonvpn.com/vpn-servers/poland", "protonvpn.com/vpn-servers/poland",
     "Jedyny dostawca, którego dziś testujemy. Bot używa darmowego serwera PL-FREE#1."),
    ("nord", "NordVPN", "https://nordvpn.com", "Nie sprawdziliśmy", "30 dni", "10", "Nie sprawdziliśmy",
     "https://nordvpn.com/pricing/", "cennik nordvpn.com",
     "Strona z listą serwerów była niedostępna dla naszego narzędzia. Dane o zwrocie i urządzeniach pochodzą z cennika."),
    ("surf", "Surfshark", "https://surfshark.com", "Tak, Warszawa", "30 dni", "Nie podano na sprawdzonej stronie", "Fire TV, Apple TV",
     "https://surfshark.com/servers/poland", "surfshark.com/servers/poland", ""),
    ("expr", "ExpressVPN", "https://www.expressvpn.com", "Tak, Warszawa", "30 dni (dla nowych klientów)", "Do 14", "Android TV, Apple TV, Fire TV",
     "https://www.expressvpn.com/vpn-server/poland-vpn", "expressvpn.com/vpn-server/poland-vpn", ""),
    ("cybr", "CyberGhost", "https://www.cyberghostvpn.com", "Nie sprawdziliśmy", "Nie sprawdziliśmy", "Nie sprawdziliśmy", "Nie sprawdziliśmy",
     "https://www.cyberghostvpn.com", "cyberghostvpn.com",
     "Nie udało się nam otworzyć strony z danymi o serwerach w Polsce. Uzupełnimy tę pozycję."),
]

LOGOS = {"proton": "https://cdn.simpleicons.org/protonvpn", "nord": "https://cdn.simpleicons.org/nordvpn", "surf": "https://cdn.simpleicons.org/surfshark",
         "expr": "https://cdn.simpleicons.org/expressvpn", "cybr": "/logos/cyberghost-icon.png"}


def facts_table():
    rows = ""
    for pid, name, url, pl, refund, dev, tv, src, srcname, note in FACTS:
        rows += (f'<tr><td><a class="prov" href="#{pid}"><img src="{LOGOS[pid]}" alt="" width="30" height="30"><span>{name}</span></a></td>'
                 f'<td data-prov-status="{pid}"><span class="muted">…</span></td><td>{pl}</td><td>{refund}</td><td>{dev}</td><td>{tv}</td>'
                 f'<td><a class="btn" href="{url}" target="_blank" rel="nofollow noopener">Strona dostawcy</a></td></tr>')
    return ('<div class="scrollx"><table class="facts"><thead><tr><th>Dostawca VPN</th><th>Nasz test</th><th>Serwer w Polsce</th><th>Zwrot pieniędzy</th>'
            '<th>Urządzenia jednocześnie</th><th>Aplikacje na TV</th><th>Oferta</th></tr></thead><tbody>' + rows + '</tbody></table></div>')


def facts_sections():
    out = ""
    for pid, name, url, pl, refund, dev, tv, src, srcname, note in FACTS:
        out += f"""<div class="provsec" id="{pid}">
  <h3><img src="{LOGOS[pid]}" alt="" width="26" height="26"> {name}</h3>
  <dl class="kv">
    <dt>Nasz test</dt><dd data-prov-status="{pid}"><span class="muted">…</span></dd>
    <dt>Serwer w Polsce</dt><dd>{pl}</dd>
    <dt>Zwrot pieniędzy</dt><dd>{refund}</dd>
    <dt>Urządzenia jednocześnie</dt><dd>{dev}</dd>
    <dt>Aplikacje na TV</dt><dd>{tv}</dd>
    <dt>Źródło danych</dt><dd><a href="{src}" target="_blank" rel="nofollow noopener">{srcname}</a>, sprawdzone {CHECKED}</dd>
  </dl>
  {f'<p class="muted">{note}</p>' if note else ''}
  <p><a class="btn" href="{url}" target="_blank" rel="nofollow noopener">Strona {name}</a></p>
</div>"""
    return out


PAGES["/porownanie-vpn"] = ("Porównanie VPN z serwerem w Polsce | Polski Streaming Monitor",
    "Pięciu dostawców VPN: serwery w Polsce, zwrot pieniędzy, liczba urządzeń i wyniki naszych testów z polskimi serwisami.",
    band('<a href="/">Polska telewizja za granicą</a> / Porównanie VPN', "Porównanie VPN z serwerem w Polsce",
         "Dwa rodzaje danych w jednej tabeli: nasze wyniki testów i fakty ze stron producentów. Zawsze widać, które jest które.",
         f'<div class="when mono"><span>Dane producentów sprawdzone: <b>{CHECKED}</b></span><span>Ostatni test: <b id="last">—</b></span></div>')
    + f"""<section class="results"><div class="wrap narrowpad">
  <div class="shead"><h2>Tabela porównawcza</h2><p>Kolumna „Nasz test” pochodzi z bota. Pozostałe kolumny to dane ze stron dostawców. „Nie sprawdziliśmy” znaczy, że nie mamy potwierdzenia ze źródła.</p></div>
  {facts_table()}
  <p class="after">Cen nie podajemy, bo zmieniają się co kilka dni i zależą od promocji. Aktualną cenę zobaczysz na stronie dostawcy.</p>
</div></section>"""
    + prose("""
<h2>Jak wybrać VPN do polskiej telewizji</h2>
<ul>
  <li><b>Serwer w Polsce.</b> Bez niego VPN nie da Ci polskiego adresu IP. To warunek konieczny.</li>
  <li><b>Wynik testu, nie reklama.</b> Każdy dostawca pisze, że „działa ze streamingiem”. Liczy się to, czy film naprawdę gra. Dlatego mamy kolumnę „Nasz test”.</li>
  <li><b>Zwrot pieniędzy.</b> Kup, sprawdź ze swoim serwisem i poproś o zwrot, jeśli nie działa. Przeczytaj warunki zwrotu przed zakupem.</li>
  <li><b>Aplikacja na telewizor.</b> Jeśli oglądasz na TV, sprawdź, czy dostawca ma aplikację na Twoją platformę.</li>
</ul>
""", "prosec", brief([("Testujemy dziś", "Proton VPN, plan darmowy"), ("Serwisy w teście", "TVP VOD, Player, TVP Sport"), ("Dane producentów", "Ze źródłem i datą")],
                     [("/tvp-vod-za-granica", "TVP VOD za granicą"), ("/player-za-granica", "Player za granicą"), ("/polsat-box-go-za-granica", "Polsat Box Go za granicą")]))
    + f'<section class="faqs"><div class="wrap"><div class="shead"><h2>Dostawcy po kolei</h2><p>Fakty i źródła. To nie są recenzje: recenzję napiszemy dopiero dla dostawcy, którego sami używaliśmy w testach.</p></div><div class="provgrid">{facts_sections()}</div></div></section>')

PAGES["/jak-testujemy"] = ("Jak testujemy VPN z polskimi serwisami | Polski Streaming Monitor",
    "Metodologia: bot łączy się z polskim serwerem VPN, sprawdza adres IP, włącza film na 60 sekund i zapisuje zrzut ekranu.",
    band('<a href="/">Polska telewizja za granicą</a> / Jak testujemy', "Jak testujemy",
         "Ten sam test każdego ranka. Wyniki publikujemy także wtedy, gdy są złe dla dostawcy.",
         WHEN)
    + """<section class="method"><div class="wrap">
  <div class="shead"><h2>Przebieg testu</h2><p id="scope"></p></div>
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
    <div><h3>Co oznaczają wyniki</h3><ul id="cats"></ul></div>
    <div><h3>Ograniczenia</h3>
      <ul class="plain">
        <li>Wynik dotyczy serwera i przeglądarki użytych w teście.</li>
        <li>Prędkość mierzymy z jednego miejsca (podanego w tabeli), nie z każdego kraju.</li>
        <li>Test używa neutralnego serwera DNS (1.1.1.1).</li>
        <li>Po nieudanej próbie bot próbuje drugi raz. Dopiero dwie nieudane próby dają wynik „Nie działa”.</li>
        <li>Nie widzimy przyczyny. „Nie działa” może wynikać z blokady, z obciążenia serwera VPN albo z awarii serwisu.</li>
      </ul>
    </div>
  </div>
</div></section>"""
    + prose("""
<h2 id="linki">Linki partnerskie</h2>
<p>Strona będzie zarabiać na linkach partnerskich: gdy kupisz VPN przez nasz link, dostaniemy prowizję, a Ty zapłacisz tyle samo. <b>Dziś żaden link na stronie nie jest jeszcze partnerski.</b> Gdy to się zmieni, oznaczymy to przy każdym przycisku.</p>
<p>Prowizja nie zmienia wyników testu ani kolejności w tabeli. Kolejność zależy tylko od liczby działających serwisów i od prędkości.</p>
<h2>Skąd są dane w porównaniu</h2>
<p>Fakty o dostawcach (serwery, zwrot pieniędzy, liczba urządzeń) pochodzą z ich własnych stron. Przy każdej pozycji jest źródło i data sprawdzenia. Gdy czegoś nie potwierdziliśmy, piszemy „Nie sprawdziliśmy”.</p>
<h2>Czego nie robimy</h2>
<ul>
  <li>Nie publikujemy wyników, których bot nie zmierzył.</li>
  <li>Nie piszemy recenzji produktów, których nie używaliśmy.</li>
  <li>Nie usuwamy złych dni z historii.</li>
</ul>
""", "prosec", brief([("Częstotliwość", "Raz dziennie, rano"), ("Kryterium", "60 s filmu bez przerwy"), ("Dowód", "Zrzut ekranu z każdej próby"), ("Historia", "30 dni, także złe dni")],
                     [("/#wyniki", "Wyniki ostatniego testu"), ("/#dowod", "Zrzuty ekranu")])))

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
.scrollx{overflow-x:auto}
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
@media (max-width:1180px){.pgrid{grid-template-columns:minmax(0,1fr);gap:32px}.side2{position:static;max-width:520px}.cnav{overflow-x:auto}.provgrid{grid-template-columns:minmax(0,1fr)}}
@media (max-width:820px){
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
        "  var LINK={proton:'https://protonvpn.com',nord:'https://nordvpn.com',surf:'https://surfshark.com',expr:'https://www.expressvpn.com',cybr:'https://www.cyberghostvpn.com'};")
    rep("var PRICE={proton:['0 zł','plan darmowy']};", "var PRICE={proton:['darmowy','0 zł']};")
    rep("'<td><button class=\"btn\" type=\"button\" data-cta aria-label=\"Sprawdź ofertę '+esc(p.name)+'\">Sprawdź ofertę</button></td></tr>'",
        "'<td><a class=\"btn\" href=\"'+LINK[p.id]+'\" target=\"_blank\" rel=\"nofollow noopener\">Strona dostawcy</a></td></tr>'")
    rep("'<button class=\"btn\" type=\"button\" data-cta>Sprawdź ofertę '+esc(p.name)+'</button></details>'",
        "'<a class=\"btn\" href=\"'+LINK[p.id]+'\" target=\"_blank\" rel=\"nofollow noopener\">Strona '+esc(p.name)+'</a></details>'")
    rep("<th>Cena za miesiąc</th><th>Oferta partnera</th>", "<th>Plan w teście</th><th>Oferta</th>")
    rep("<div><span>Cena za miesiąc</span>", "<div><span>Plan w teście</span>")
    rep("Płatnych serwisów (Polsat Box Go, Canal+ Online) jeszcze nie testujemy.'", "Płatnych serwisów jeszcze nie testujemy.'")
    rep("    render();\n  }",
        "    all('[data-svc]',function(el){var sid=el.dataset.svc,h='';RUN.providers.filter(function(p){return p.tested}).forEach(function(p){var r=p.services[sid];if(!r)return;"
        "h+='<div class=\"svcrow\">'+logo(p.id)+'<b>'+esc(p.name)+(p.plan?' ('+esc(p.plan)+')':'')+'</b>'+st(r.status)+'<span class=\"muted\">Test: '+fmtDT(r.tested_at)+(r.reason?'. '+esc(r.reason):'')+'</span>'"
        "+(r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\">zrzut ekranu</a>':'<span></span>')+'</div>'});"
        "el.innerHTML=h||'<p class=\"muted\" style=\"padding:14px 0\">Tego serwisu jeszcze nie testujemy.</p>'});\n"
        "    all('[data-prov-status]',function(el){var p=RUN.providers.filter(function(x){return x.id===el.dataset.provStatus})[0];"
        "el.innerHTML=p&&p.tested?SVON.map(function(s){return '<span class=\"pst\">'+esc(s.name)+':'+st(stat(p,s.id))+'</span>'}).join(''):st('none')});\n"
        "    all('[data-shot]',function(el){var p=best(),r=p&&p.services&&p.services[el.dataset.shot];el.innerHTML=r&&r.shot?'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"/'+esc(r.shot)+'\" alt=\"Zrzut ekranu z testu\" loading=\"lazy\" width=\"1440\" height=\"900\"></a>':''});\n"
        "    render();\n  }")
    rep("get('data/latest.json'),get('data/history.json')", "get('/data/latest.json'),get('/data/history.json')")
    for old in ["'logos/tvpvod.png'", "'logos/player.svg'", "'logos/polsat.svg'", "'logos/canal.svg'", "'logos/cyberghost-icon.png'"]:
        rep(old, "'/" + old[1:])
    rep("'<img class=\"t\" src=\"'+esc(rr.shot)+'\"", "'<img class=\"t\" src=\"/'+esc(rr.shot)+'\"")
    rep("'<a href=\"'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"'+esc(r.shot)+'\"", "'<a href=\"/'+esc(r.shot)+'\" target=\"_blank\" rel=\"noopener\"><img src=\"/'+esc(r.shot)+'\"")
    (SITE / "app.js").write_text(s)


def main():
    (SITE / "style.css").write_text((HERE / "base.css").read_text() + EXTRA_CSS)
    build_js()
    for path, (title, desc, body) in PAGES.items():
        name = "index.html" if path == "/" else path.strip("/") + ".html"
        (SITE / name).write_text(layout(path, title, desc, body))
    urls = "".join(f"<url><loc>{DOMAIN}{'' if p == '/' else p}</loc></url>" for p in PAGES)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    (SITE / "robots.txt").write_text(("User-agent: *\nAllow: /\n" if INDEXABLE else "User-agent: *\nDisallow: /\n") + f"Sitemap: {DOMAIN}/sitemap.xml\n")
    print("built", len(PAGES), "pages")


if __name__ == "__main__":
    main()
