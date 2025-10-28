from __future__ import annotations

import aiohttp
from urllib import robotparser
from urllib.parse import urlparse
import logging


class RobotsChecker:
    def __init__(self, session: aiohttp.ClientSession, user_agent: str, timeout: int):
        self.session = session
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: dict[str, robotparser.RobotFileParser] = {}

    async def _fetch_robots(self, base_url: str) -> robotparser.RobotFileParser:
        parsed = urlparse(base_url)
        host = parsed.hostname
        scheme = parsed.scheme or "http"
        robots_url = f"{scheme}://{host}/robots.txt" if host else ""
        rp = robotparser.RobotFileParser()
        if not robots_url:
            rp.parse([])
            return rp
        try:
            async with self.session.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=self.timeout) as resp:
                if resp.status == 200:
                    text = await resp.text(errors="ignore")
                    rp.parse(text.splitlines())
                else:
                    rp.parse([])
        except Exception as e:
            logging.debug("robots.txt fetch error for %s: %s", robots_url, e)
            rp.parse([])
        return rp

    async def allowed(self, url: str) -> bool:
        try:
            host = urlparse(url).hostname
            if not host:
                return True
            if host not in self._cache:
                self._cache[host] = await self._fetch_robots(url)
            return self._cache[host].can_fetch(self.user_agent, url)
        except Exception:
            return True

