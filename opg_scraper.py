"""OPG Scraper CLI wrapper.

Legal and safety notice: use only for lawful, legitimate purposes and respect privacy laws (GDPR) and opt-out requests.
For detailed instructions, see README.md.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, List

from opg_scraper_pkg.cli import parse_args, setup_logging, main_async, run_tests


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    setup_logging(log_file=args.log_file, verbose=True)
    if args.run_tests:
        return run_tests()
    try:
        asyncio.run(main_async(args))
        return 0
    except KeyboardInterrupt:
        logging.warning("Prekinuto od strane korisnika.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
