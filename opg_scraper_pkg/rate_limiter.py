from __future__ import annotations

import asyncio
import time


class HostRateLimiter:
    def __init__(self, delay_seconds: float):
        self.delay = delay_seconds
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}

    async def throttle(self, host: str):
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        lock = self._locks[host]
        async with lock:
            now = time.monotonic()
            last = self._last.get(host, 0.0)
            wait = self.delay - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[host] = time.monotonic()

