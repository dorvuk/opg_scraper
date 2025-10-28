from __future__ import annotations

import logging
from typing import Callable, List, Optional
from urllib.parse import quote_plus, urlparse

import aiohttp
from bs4 import BeautifulSoup

from .config import USER_AGENT
from .robots import RobotsChecker
from .rate_limiter import HostRateLimiter
from .utils import canonicalize_url


ProgressCallback = Optional[Callable[[int], None]]  # receives increment value


class Searcher:
    def __init__(self, session: aiohttp.ClientSession, robots: RobotsChecker, limiter: HostRateLimiter, dry_run: bool, timeout: int):
        self.session = session
        self.robots = robots
        self.limiter = limiter
        self.dry_run = dry_run
        self.timeout = timeout

    @staticmethod
    def county_queries(county: str) -> List[str]:
        return [
            f"OPG {county}",
            f"opg {county} email",
            f"kontakt OPG {county}",
            f"obiteljsko poljoprivredno gospodarstvo {county}",
            f"OPG {county} kontakt email",
        ]

    async def _fetch_text(self, url: str) -> str:
        if self.dry_run:
            logging.info("[dry-run] GET %s", url)
            return ""
        if not await self.robots.allowed(url):
            logging.debug("Robots disallow: %s", url)
            return ""
        host = urlparse(url).hostname or ""
        await self.limiter.throttle(host)
        try:
            async with self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout, allow_redirects=True) as resp:
                if resp.status == 429:
                    return ""
                resp.raise_for_status()
                return await resp.text(errors="ignore")
        except Exception as e:
            logging.debug("Fetch error %s: %s", url, e)
            return ""

    async def search_duckduckgo(self, query: str, max_results: int = 20) -> List[str]:
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}&kl=hr-hr"
        html = await self._fetch_text(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        results: list[str] = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href and href.startswith("http"):
                results.append(canonicalize_url(href))
            if len(results) >= max_results:
                break
        if not results:
            for a in soup.select("a[href]"):
                href = a.get("href")
                if href and href.startswith("http"):
                    results.append(canonicalize_url(href))
                if len(results) >= max_results:
                    break
        return results

    async def search_bing(self, query: str, max_results: int = 20) -> List[str]:
        url = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=hr-hr"
        html = await self._fetch_text(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        results: list[str] = []
        for h2 in soup.select("li.b_algo h2"):
            a = h2.find("a", href=True)
            if a and a.get("href", "").startswith("http"):
                results.append(canonicalize_url(a.get("href")))
            if len(results) >= max_results:
                break
        if not results:
            for a in soup.select("a[href]"):
                href = a.get("href")
                if href and href.startswith("http"):
                    results.append(canonicalize_url(href))
                if len(results) >= max_results:
                    break
        return results

    async def search_google_fallback(self, query: str, max_results: int = 10) -> List[str]:
        url = f"https://www.google.com/search?q={quote_plus(query)}&hl=hr"
        allowed = await self.robots.allowed(url)
        if not allowed:
            logging.info("Skipping Google search due to robots disallow: %s", url)
            return []
        html = await self._fetch_text(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        results: list[str] = []
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("/url?"):
                try:
                    from urllib.parse import parse_qs

                    qs = parse_qs(urlparse(href).query)
                    if "q" in qs and qs["q"]:
                        target = qs["q"][0]
                        if target.startswith("http"):
                            results.append(canonicalize_url(target))
                except Exception:
                    pass
            elif href.startswith("http"):
                results.append(canonicalize_url(href))
            if len(results) >= max_results:
                break
        return results

    async def discover_seeds(self, county: str, max_results: int, on_progress: ProgressCallback = None) -> List[str]:
        seeds: list[str] = []
        for q in self.county_queries(county):
            for engine in ("bing", "duckduckgo", "google"):
                if engine == "bing":
                    res = await self.search_bing(q, max_results=max_results)
                elif engine == "duckduckgo":
                    res = await self.search_duckduckgo(q, max_results=max_results)
                else:
                    res = await self.search_google_fallback(q, max_results=min(10, max_results))
                for url in res:
                    if url not in seeds:
                        seeds.append(url)
                if on_progress:
                    on_progress(1)
                if len(seeds) >= max_results:
                    break
            if len(seeds) >= max_results:
                break
        return seeds[:max_results]

