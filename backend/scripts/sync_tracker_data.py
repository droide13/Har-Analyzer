#!/usr/bin/env python3
"""Regenerate backend/app/data/{trackers.csv,known_ids/} from the
ID-Graph-Tables submodule (see /ID-Graph-Tables at the repo root).

If the submodule hasn't been cloned/initialized, this is a silent no-op --
whatever's already committed under backend/app/data/ is left alone, so the
app works either way (see readme.md). Run this by hand (or via dev.sh, which
calls it automatically) after updating the submodule to a newer commit.

What it does:
- Reads ID-Graph-Tables/src/data/studied-services.txt for the list of
  "studied" vendor keys -- NOT every file in data/research/, since that
  folder can contain stale/unreviewed JSONs for orgs no longer on the list.
- Copies each studied vendor's research/<key>.json verbatim into
  backend/app/data/known_ids/ (used for identifier *name* matching, e.g.
  "id5id" -> "ID5").
- Builds backend/app/data/trackers.csv (used for *domain* matching) by
  exploding output/merged_trackers.csv's comma-joined Domains column into
  one row per domain, then overlaying each studied vendor's own researched
  Domains -- which take precedence, since they're curated and often include
  specific subdomains (e.g. rp.liadm.com) with far more precise notes than
  the broad crawl-derived table has for the parent domain.
"""

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SUBMODULE_ROOT = REPO_ROOT / "ID-Graph-Tables" / "src"
STUDIED_SERVICES_FILE = SUBMODULE_ROOT / "data" / "studied-services.txt"
RESEARCH_DIR = SUBMODULE_ROOT / "data" / "research"
MERGED_TRACKERS_CSV = SUBMODULE_ROOT / "output" / "merged_trackers.csv"

DATA_DIR = REPO_ROOT / "backend" / "app" / "data"
TRACKERS_CSV_OUT = DATA_DIR / "trackers.csv"
KNOWN_IDS_DIR_OUT = DATA_DIR / "known_ids"

# Category label for a domain that came from a studied vendor's own manual
# research rather than the broad Ghostery/Tracker Radar crawl -- distinct
# from (and takes precedence over) whatever, if anything, that broad table's
# own `category` column says for the same domain.
MANUAL_RESEARCH_CATEGORY = "identity_graph"


def read_studied_services() -> list[str]:
    """Vendor keys from studied-services.txt, one per non-blank line."""
    text = STUDIED_SERVICES_FILE.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def load_broad_tracker_domains() -> dict[str, dict[str, str]]:
    """domain -> {service, category, description} from merged_trackers.csv,
    exploding its comma-joined Domains column into one entry per domain."""
    domains: dict[str, dict[str, str]] = {}
    with MERGED_TRACKERS_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            service = (row.get("Service") or "").strip()
            category = (row.get("category") or "").strip()
            raw_domains = row.get("Domains") or ""
            for domain in (d.strip() for d in raw_domains.split(",")):
                if domain:
                    domains[domain] = {"service": service, "category": category, "description": ""}
    return domains


def load_studied_vendor_domains(studied: list[str]) -> dict[str, dict[str, str]]:
    """domain -> {service, category, description} from each studied vendor's
    own researched Domains list, meant to overlay (take precedence over) the
    broad table above."""
    domains: dict[str, dict[str, str]] = {}
    for key in studied:
        json_path = RESEARCH_DIR / f"{key}.json"
        if not json_path.is_file():
            print(f"warning: {key} is in studied-services.txt but {json_path} doesn't exist -- skipping")
            continue

        data: dict[str, Any] = json.loads(json_path.read_text(encoding="utf-8"))
        research = data.get("research", {})
        service = str(research.get("Service", key))
        for entry in research.get("Domains", []):
            domain = str(entry.get("Domain", "")).strip()
            if not domain:
                continue
            description = str(entry.get("Description") or entry.get("Notes") or "").strip()
            domains[domain] = {"service": service, "category": MANUAL_RESEARCH_CATEGORY, "description": description}
    return domains


def write_trackers_csv(domains: dict[str, dict[str, str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with TRACKERS_CSV_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "service", "category", "description"])
        writer.writeheader()
        for domain in sorted(domains):
            writer.writerow({"domain": domain, **domains[domain]})


def sync_known_ids(studied: list[str]) -> None:
    """Replace backend/app/data/known_ids/ with a verbatim copy of each
    studied vendor's research JSON -- fully regenerated each run so a vendor
    removed from studied-services.txt doesn't leave a stale file behind."""
    if KNOWN_IDS_DIR_OUT.is_dir():
        for stale in KNOWN_IDS_DIR_OUT.glob("*.json"):
            stale.unlink()
    KNOWN_IDS_DIR_OUT.mkdir(parents=True, exist_ok=True)

    for key in studied:
        json_path = RESEARCH_DIR / f"{key}.json"
        if not json_path.is_file():
            continue  # already warned about in load_studied_vendor_domains
        (KNOWN_IDS_DIR_OUT / f"{key}.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    if not STUDIED_SERVICES_FILE.is_file():
        print(f"ID-Graph-Tables submodule not initialized ({STUDIED_SERVICES_FILE} not found) -- "
              f"leaving {DATA_DIR} as-is.")
        return

    studied = read_studied_services()
    print(f"Studied services: {', '.join(studied)}")

    domains = load_broad_tracker_domains()
    domains.update(load_studied_vendor_domains(studied))
    write_trackers_csv(domains)
    sync_known_ids(studied)

    print(f"Wrote {TRACKERS_CSV_OUT} ({len(domains)} domains) and {len(studied)} known-ID files to {KNOWN_IDS_DIR_OUT}")


if __name__ == "__main__":
    main()
