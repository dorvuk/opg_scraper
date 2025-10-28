from __future__ import annotations

USER_AGENT = "MagicNet-OPG-Scraper/1.0 (+mailto:marketing@mtnet.hr)"
DEFAULT_COUNTIES = [
    "Međimurska",
    "Varaždinska",
    "Koprivničko-Križevačka",
    "Krapinsko-Zagorska",
]

DEFAULT_DEPTH = 2
DEFAULT_RATE_LIMIT_SECONDS = 1.0
DEFAULT_REQUEST_TIMEOUT = 20
DEFAULT_MAX_RESULTS_PER_COUNTY = 50

ROLE_BASED_PREFIXES = (
    "info@",
    "contact@",
    "kontakt@",
    "webmaster@",
    "postmaster@",
    "admin@",
    "office@",
)

OPT_OUT_KEYWORDS = (
    "no spam",
    "do not contact",
    "do-not-contact",
    "do-not-email",
    "dont contact",
    "do not email",
    "do-not-mail",
    "no marketing",
    "opt-out",
    "unsubscribe",
    "privacy policy",
    "ne šaljite spam",
    "ne šaljite neželjenu poštu",
    "neželjena pošta",
    "ne zelimo spam",
    "ne želimo spam",
    "bez marketinga",
    "ne kontaktirajte",
    "ne-kontaktirajte",
    "odjava",
    "privatnost",
    "zaštita podataka",
)

