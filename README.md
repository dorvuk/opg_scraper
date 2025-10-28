# OPG Scraper

Sakupljanje javno dostupnih email adresa obiteljskih poljoprivrednih gospodarstava (OPG) po županijama u Hrvatskoj.

VAŽNO – Zakonitost i privatnost
- Koristite ovaj alat isključivo za zakonite i legitimne svrhe te uz poštivanje privatnosti.
- Poštujte GDPR i lokalne propise; prikupljene adrese koristite uz privolu ili valjani legitimni interes.
- Poštujte zahtjeve za odjavom i svaku eksplicitnu napomenu o zabrani marketinških poruka.

Značajke
- Pretraga weba (Bing, DuckDuckGo; Google fallback samo ako robots.txt dopušta) po upitima npr. „OPG {županija}”, „kontakt OPG {županija}”.
- Poštivanje robots.txt i per-host ograničenje (1 zahtjev/sek).
- Ekstrakcija email adresa (mailto, regex, JSON-LD), normalizacija i validacija.
- Filtriranje role-based adresa (info@, contact@) osim ako su jasno OPG-specifične; opcija za uključivanje.
- Opcija poštivanja „opt-out/no-spam/privatnost” napomena na stranici.
- Praćenje napretka preko progress barova (pretraga i ukupni crawl stranica).
- Dedupirani CSV i zasebni JSON audit.

Instalacija
```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install aiohttp beautifulsoup4 lxml tqdm
# (opcionalno) pip install python-whois
```

Pokretanje
```
python opg_scraper.py --output opg_emails.csv
```

Primjeri
```
# Zadane županije (Međimurska, Varaždinska, Koprivničko-Križevačka, Krapinsko-Zagorska)
python opg_scraper.py --output opg_emails.csv

# Odabrane županije
python opg_scraper.py Međimurska Varaždinska --max-results-per-county 50

# Županije iz datoteke (po liniji)
python opg_scraper.py --counties-file zupanije.txt --depth 2 --max-results-per-county 100

# Dry-run – bez dohvaćanja (samo planirani URL-ovi)
python opg_scraper.py Međimurska --dry-run

# Poštuj opt-out napomene
python opg_scraper.py Međimurska --respect-opt-out

# Uključi role-based adrese (npr. info@)
python opg_scraper.py Međimurska --include-role-emails
```

CSV izlaz – stupci
`email, name, county, source_url, page_title, discovery_method, date_found`

Napomena o tražilicama
- Google `/search` često zabranjuje automatizirano dohvaćanje u robots.txt; alat to provjerava i preskače nedopuštene URL-ove.
- Umjesto API ključeva koriste se javne HTML stranice rezultata uz oprez; ako želite dodati API-je, moguće je dopuniti konfiguraciju.

Testovi
```
python -m unittest
```

Struktura projekta
```
.
├── opg_scraper.py          # CLI ulazna točka
├── opg_scraper_pkg/
│   ├── __init__.py
│   ├── cli.py              # Argumenti, logging, orkestracija i progress barovi
│   ├── config.py           # Konstante i postavke
│   ├── crawl.py            # Crawler + EmailRecord
│   ├── extractor.py        # EmailExtractor
│   ├── output.py           # CSV i JSON zapis
│   ├── rate_limiter.py     # Per-host throttling
│   ├── robots.py           # RobotsChecker
│   └── search.py           # Searcher (Bing, DDG, Google fallback)
└── tests/
    ├── test_extractor.py
    └── test_robots.py
```

Licenca
- Ovaj repozitorij ne uključuje licencu. Ne zaboravite provjeriti i poštovati pravila korištenja web-stranica koje se indeksiraju.

