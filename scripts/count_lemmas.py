#!/usr/bin/env python3
"""
Count lemmas in index files and show statistics.

Usage:
    python scripts/count_lemmas.py                     # All indexes in data/
    python scripts/count_lemmas.py data/vstd_lemma_index.json
    python scripts/count_lemmas.py data/*.json
"""

import json
import sys
from pathlib import Path


def count_lemmas(index_file: Path) -> dict:
    """Count lemmas and specs in an index file."""
    with open(index_file) as f:
        data = json.load(f)

    lemmas = data.get("lemmas", [])
    total = len(lemmas)

    if total == 0:
        return {"file": index_file.name, "total": 0, "with_specs": 0, "pct": 0}

    with_specs = len(
        [lem for lem in lemmas if lem.get("requires_clauses") or lem.get("ensures_clauses")]
    )
    pct = 100 * with_specs / total

    return {"file": index_file.name, "total": total, "with_specs": with_specs, "pct": pct}


def main():
    # Determine which files to check
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Default: all *_lemma_index.json files in data/
        data_dir = Path(__file__).parent.parent / "data"
        files = sorted(data_dir.glob("*_lemma_index.json"))

    if not files:
        print("No index files found.")
        print("Usage: python scripts/count_lemmas.py [index_file.json ...]")
        return 1

    print(f"{'Index File':<45} {'Total':>8} {'With Specs':>12} {'Coverage':>10}")
    print("-" * 77)

    total_lemmas = 0
    total_with_specs = 0

    for f in files:
        if not f.exists():
            print(f"⚠️  File not found: {f}")
            continue

        try:
            stats = count_lemmas(f)
            print(
                f"{stats['file']:<45} {stats['total']:>8} {stats['with_specs']:>12} {stats['pct']:>9.0f}%"
            )
            total_lemmas += stats["total"]
            total_with_specs += stats["with_specs"]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Error reading {f}: {e}")

    if len(files) > 1 and total_lemmas > 0:
        print("-" * 77)
        total_pct = 100 * total_with_specs / total_lemmas
        print(f"{'TOTAL':<45} {total_lemmas:>8} {total_with_specs:>12} {total_pct:>9.0f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
