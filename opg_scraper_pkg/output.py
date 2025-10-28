from __future__ import annotations

import csv
import json
import os
from typing import List, Set

from .crawl import EmailRecord


class CSVWriter:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.fieldnames = [
            "email",
            "name",
            "county",
            "source_url",
            "page_title",
            "discovery_method",
            "date_found",
        ]

    def write(self, records: List[EmailRecord]):
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        seen: Set[str] = set()
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            for r in records:
                key = r.email.lower()
                if key in seen:
                    continue
                seen.add(key)
                writer.writerow({
                    "email": r.email,
                    "name": r.name,
                    "county": r.county,
                    "source_url": r.source_url,
                    "page_title": r.page_title,
                    "discovery_method": r.discovery_method,
                    "date_found": r.date_found,
                })

    @staticmethod
    def audit_path_from_csv(csv_path: str) -> str:
        base, _ = os.path.splitext(csv_path)
        return base + ".json"

    def write_audit(self, csv_path: str, audit_pages: List[dict]):
        audit_path = self.audit_path_from_csv(csv_path)
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump({"pages": audit_pages}, f, ensure_ascii=False, indent=2)

