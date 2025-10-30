from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from .config import (
    DEFAULT_COUNTIES,
    DEFAULT_DEPTH,
    DEFAULT_MAX_RESULTS_PER_COUNTY,
    DEFAULT_RATE_LIMIT_SECONDS,
    DEFAULT_REQUEST_TIMEOUT,
    USER_AGENT,
)


def setup_logging(log_file: Optional[str] = None, verbose: bool = True):
    log_level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OPG scraper: javno dostupne email adrese OPG-ova u HR županijama.")
    p.add_argument("counties", nargs="*", help="Popis županija (npr. Međimurska Varaždinska)")
    p.add_argument("--counties-file", help="Put do datoteke s jednom županijom po liniji")
    p.add_argument("--max-results-per-county", type=int, default=DEFAULT_MAX_RESULTS_PER_COUNTY, help="Maksimalan broj seed rezultata pretrage po županiji")
    p.add_argument("--max-pages-per-county", type=int, default=200, help="Maksimalan broj stranica za crawl po županiji (ukupno preko hostova)")
    p.add_argument("--depth", type=int, default=DEFAULT_DEPTH, help="Maksimalna dubina internih linkova")
    p.add_argument("--output", default="opg_emails.csv", help="Put do izlaznog CSV-a")
    p.add_argument("--dry-run", action="store_true", help="Ne dohvaćaj, samo ispiši planirane zahtjeve")
    p.add_argument("--respect-opt-out", action="store_true", help="Filtriraj adrese s web-stranica s eksplicitnom napomenom o nekontaktiranju/privatnosti")
    p.add_argument("--include-role-emails", action="store_true", help="Uključi role-based adrese (npr. info@)")
    p.add_argument("--log-file", default="opg_scraper.log", help="Put do log datoteke")
    p.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT, help="HTTP timeout u sekundama")
    p.add_argument("--run-tests", action="store_true", help="Pokreni osnovne testove i izađi")
    p.add_argument("--no-progress", action="store_true", help="Onemogući progress barove")
    return p.parse_args(argv)


def load_counties(args: argparse.Namespace) -> List[str]:
    if args.counties:
        return list(args.counties)
    if args.counties_file:
        with open(args.counties_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return list(DEFAULT_COUNTIES)


async def run_for_county(
    county: str,
    session,
    limiter,
    args: argparse.Namespace,
    pages_pbar=None,
):
    # Local imports to avoid requiring aiohttp for --run-tests
    from tqdm import tqdm
    from .search import Searcher
    from .extractor import EmailExtractor
    from .crawl import Crawler

    searcher = Searcher(session, limiter, dry_run=args.dry_run, timeout=args.timeout)
    extractor = EmailExtractor()
    crawler = Crawler(
        session=session,
        limiter=limiter,
        extractor=extractor,
        depth=args.depth,
        timeout=args.timeout,
        dry_run=args.dry_run,
        respect_opt_out=args.respect_opt_out,
        include_role_emails=args.include_role_emails,
    )

    search_steps_total = len(Searcher.county_queries(county))
    search_pbar = None if args.no_progress else tqdm(total=search_steps_total, desc=f"Search {county}", leave=False)
    on_search_step = (lambda n: search_pbar.update(n)) if search_pbar else None

    logging.info("[%s] Traženje seed URL-ova...", county)
    seeds = await searcher.discover_seeds(county, max_results=args.max_results_per_county, on_progress=on_search_step)
    if search_pbar:
        search_pbar.close()
    logging.info("[%s] Pronađeno %d seed URL-ova", county, len(seeds))
    if args.dry_run:
        for s in seeds:
            logging.info("[dry-run] plan crawl seed: %s", s)
        return [], []

    records = []
    audit_pages = []

    by_host: dict[str, List[str]] = {}
    for s in seeds:
        host = urlparse(s).hostname or s
        by_host.setdefault(host, []).append(s)

    remaining = args.max_pages_per_county
    for host, host_seeds in by_host.items():
        if remaining <= 0:
            break
        per_host_pages = max(5, min(remaining, 50))
        logging.info("[%s] Crawl host %s (limit %d)", county, host, per_host_pages)
        for seed in host_seeds[:2]:
            recs, pages = await crawler.crawl_host(seed, county, max_pages=per_host_pages, on_page=(lambda n: pages_pbar.update(n) if pages_pbar else None))
            records.extend(recs)
            audit_pages.extend(pages)
            remaining -= per_host_pages
            if remaining <= 0:
                break

    return records, audit_pages


async def main_async(args: argparse.Namespace):
    # Local imports to avoid requiring aiohttp for --run-tests
    from tqdm import tqdm
    import aiohttp
    from .rate_limiter import HostRateLimiter
    from .output import CSVWriter

    counties = load_counties(args)
    logging.info("Županije: %s", ", ".join(counties))
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        limiter = HostRateLimiter(delay_seconds=DEFAULT_RATE_LIMIT_SECONDS)

        all_records = []
        all_audit_pages = []

        total_pages = len(counties) * args.max_pages_per_county
        pages_pbar = None if args.no_progress else tqdm(total=total_pages, desc="Crawling pages", leave=True)
        try:
            for county in counties:
                recs, audit = await run_for_county(county, session, limiter, args, pages_pbar)
                all_records.extend(recs)
                all_audit_pages.extend(audit)
        finally:
            if pages_pbar:
                pages_pbar.close()

    if args.dry_run:
        logging.info("Dry-run završen; bez pisanja CSV-a.")
        return

    from .crawl import EmailRecord  # type: ignore

    dedup_map: dict[str, EmailRecord] = {}
    for r in all_records:
        dedup_map.setdefault(r.email.lower(), r)
    deduped = list(dedup_map.values())

    writer = CSVWriter(args.output)
    writer.write(deduped)
    writer.write_audit(args.output, all_audit_pages)
    logging.info("Zapisano %d jedinstvenih email adresa u %s", len(deduped), args.output)
    logging.info("Sirovi audit spremljen u %s", writer.audit_path_from_csv(args.output))


def run_tests() -> int:
    import unittest
    print("Running tests...")
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1
