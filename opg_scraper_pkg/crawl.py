from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from .config import USER_AGENT
from .extractor import EmailExtractor
from .rate_limiter import HostRateLimiter
from .robots import RobotsChecker
from .utils import (
    canonicalize_url,
    contains_opt_out,
    extract_page_title,
    guess_name_from_page,
    is_role_based,
    same_host,
    utc_now_iso,
)


ProgressCallback = Optional[Callable[[int], None]]  # receives increment value


@dataclass
class EmailRecord:
    email: str
    name: str
    county: str
    source_url: str
    page_title: str
    discovery_method: str
    date_found: str


class Crawler:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        robots: RobotsChecker,
        limiter: HostRateLimiter,
        extractor: EmailExtractor,
        depth: int,
        timeout: int,
        dry_run: bool,
        respect_opt_out: bool,
        include_role_emails: bool,
    ):
        self.session = session
        self.robots = robots
        self.limiter = limiter
        self.extractor = extractor
        self.depth = depth
        self.timeout = timeout
        self.dry_run = dry_run
        self.respect_opt_out = respect_opt_out
        self.include_role_emails = include_role_emails

    async def _fetch_html(self, url: str) -> str:
        if self.dry_run:
            logging.info("[dry-run] GET %s", url)
            return ""
        if not await self.robots.allowed(url):
            logging.debug("Robots disallow: %s", url)
            return ""
        host = urlparse(url).hostname or ""
        await self.limiter.throttle(host)
        backoff = 1.0
        for _ in range(4):
            try:
                async with self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout, allow_redirects=True) as resp:
                    if resp.status in (429, 503):
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    resp.raise_for_status()
                    return await resp.text(errors="ignore")
            except Exception as e:
                logging.debug("Fetch error %s: %s", url, e)
                await asyncio.sleep(backoff)
                backoff *= 2
        return ""

    async def crawl_host(self, seed_url: str, county: str, max_pages: int, on_page: ProgressCallback = None) -> Tuple[List[EmailRecord], List[dict]]:
        visited: Set[str] = set()
        queue: List[Tuple[str, int, str]] = [(canonicalize_url(seed_url), 0, "search_seed")]
        out_records: List[EmailRecord] = []
        audit_pages: List[dict] = []

        while queue and len(visited) < max_pages:
            url, depth, source = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if on_page:
                on_page(1)

            html = await self._fetch_html(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "lxml")
            title = extract_page_title(soup)
            text = soup.get_text(" ", strip=True)
            opt_out = contains_opt_out(text)

            emails = self.extractor.extract(html, url)
            if emails:
                name_hint = guess_name_from_page(soup)
                for email, how in emails:
                    if not self.include_role_emails and is_role_based(email):
                        if not ("opg" in (title or "").lower() or "opg" in text.lower()):
                            continue
                    if self.respect_opt_out and opt_out:
                        continue
                    out_records.append(
                        EmailRecord(
                            email=email,
                            name=name_hint,
                            county=county,
                            source_url=url,
                            page_title=title,
                            discovery_method=how,
                            date_found=utc_now_iso(),
                        )
                    )

            audit_pages.append(
                {
                    "url": url,
                    "title": title,
                    "county": county,
                    "timestamp": utc_now_iso(),
                    "found_emails": [e for e, _ in emails],
                    "opt_out_detected": opt_out,
                    "source": source,
                }
            )

            if depth < self.depth:
                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    if not href:
                        continue
                    nxt = urljoin(url, href)
                    if not nxt.startswith("http"):
                        continue
                    if not same_host(seed_url, nxt):
                        continue
                    nxt = canonicalize_url(nxt)
                    if nxt in visited:
                        continue
                    if any(k in href.lower() for k in ("kontakt", "contact", "email", "onama", "o-nama", "about", "opg")):
                        queue.insert(0, (nxt, depth + 1, "internal_contact_link"))
                    else:
                        queue.append((nxt, depth + 1, "internal_link"))

        return out_records, audit_pages

