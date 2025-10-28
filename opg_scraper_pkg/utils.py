from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from .config import ROLE_BASED_PREFIXES, OPT_OUT_KEYWORDS


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_email(email: str) -> str:
    e = email.strip().strip(".,;:<>()[]{}'\"")
    if "@" in e:
        local, domain = e.split("@", 1)
        return f"{local}@{domain.lower()}"
    return e.lower()


def is_valid_email(email: str) -> bool:
    EMAIL_RE = re.compile(r"(?i)^[A-Z0-9._%+\-']{1,64}@[A-Z0-9.-]{1,253}\.[A-Z]{2,63}$")
    return bool(EMAIL_RE.match(email))


def is_role_based(email: str) -> bool:
    el = email.lower()
    return any(el.startswith(p) for p in ROLE_BASED_PREFIXES)


def same_host(u1: str, u2: str) -> bool:
    try:
        p1 = urlparse(u1)
        p2 = urlparse(u2)
        return p1.hostname == p2.hostname
    except Exception:
        return False


def canonicalize_url(url: str) -> str:
    p = urlparse(url)
    scheme = p.scheme or "http"
    netloc = p.netloc
    path = p.path or "/"
    query = f"?{p.query}" if p.query else ""
    return f"{scheme}://{netloc}{path}{query}"


def looks_like_contact_link(href: str) -> bool:
    key_parts = ("kontakt", "contact", "email", "o-nama", "onama", "about", "opg", "gospodarstvo")
    l = href.lower()
    return any(k in l for k in key_parts)


def contains_opt_out(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in OPT_OUT_KEYWORDS)


def extract_page_title(soup) -> str:
    title = (soup.title.string or "").strip() if soup.title else ""
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            title = og.get("content").strip()
    return title[:200]


def guess_name_from_page(soup) -> str:
    import re as _re
    title = extract_page_title(soup)
    if title:
        m = _re.search(r"\bOPG\s+[^|\-–—]+", title, _re.IGNORECASE)
        if m:
            return m.group(0).strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        text = h1.get_text(strip=True)
        if _re.search(r"\bOPG\b", text, _re.IGNORECASE):
            return text[:200]
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        return og.get("content").strip()[:200]
    return title or ""

