from __future__ import annotations

import json
import re
from typing import List, Tuple

from bs4 import BeautifulSoup

from .utils import normalize_email, is_valid_email


class EmailExtractor:
    MAILTO_RE = re.compile(r"(?i)mailto:([^?\s#]+)")
    EMAIL_CANDIDATE_RE = re.compile(r"(?i)([A-Z0-9._%+\-']{1,64}@[A-Z0-9.-]{1,253}\.[A-Z]{2,63})")

    def extract(self, html: str, base_url: str) -> List[Tuple[str, str]]:
        results: list[tuple[str, str]] = []
        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            m = self.MAILTO_RE.search(href)
            if m:
                email = normalize_email(m.group(1))
                if is_valid_email(email):
                    results.append((email, "mailto"))

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.get_text(strip=True))
                emails: list[str] = []
                if isinstance(data, dict):
                    if "email" in data:
                        emails = [data.get("email")]
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "email" in item:
                            emails.append(item.get("email"))
                for e in emails:
                    if e:
                        email = normalize_email(str(e))
                        if is_valid_email(email):
                            results.append((email, "json-ld"))
            except Exception:
                pass

        text = soup.get_text(" ", strip=True)
        for m in self.EMAIL_CANDIDATE_RE.finditer(text):
            email = normalize_email(m.group(1))
            if is_valid_email(email):
                results.append((email, "regex"))

        seen: dict[str, tuple[str, str]] = {}
        for email, how in results:
            seen.setdefault(email.lower(), (email, how))
        return list(seen.values())

