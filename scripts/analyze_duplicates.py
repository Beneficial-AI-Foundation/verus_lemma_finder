#!/usr/bin/env python3
"""
Analyze duplicate detection results and categorize patterns.

Usage:
    # First run duplicate detection to generate JSON:
    python -m verus_lemma_finder detect-duplicates index.json -o duplicates.json --similar

    # Then analyze the results:
    python scripts/analyze_duplicates.py duplicates.json
    python scripts/analyze_duplicates.py duplicates.json --markdown  # Output as markdown
"""

import argparse
import json
import sys
from pathlib import Path


def categorize_similar_pairs(duplicates: list[dict]) -> dict[str, list[dict]]:
    """Categorize similar pairs by pattern type."""
    patterns = {
        "limb_variants": [],
        "incremental_lemmas": [],
        "symmetric_variants": [],
        "comparison_variants": [],
        "other": [],
    }

    for d in duplicates:
        if d["type"] != "similar":
            continue

        l1, l2 = d["lemma1"], d["lemma2"]
        combined = l1 + l2

        if "limb" in l1.lower() and "limb" in l2.lower():
            patterns["limb_variants"].append(d)
        elif any(x in l1 for x in ["_01", "_012", "_0123", "_01234"]):
            patterns["incremental_lemmas"].append(d)
        elif any(x in combined for x in ["_l_", "_r_", "left", "right"]):
            patterns["symmetric_variants"].append(d)
        elif ("_le" in combined and "_lt" in combined) or (
            "mul_le" in combined and "mul_lt" in combined
        ):
            patterns["comparison_variants"].append(d)
        else:
            patterns["other"].append(d)

    return patterns


def print_text_report(data: dict) -> None:
    """Print analysis as text."""
    duplicates = data["duplicates"]

    # Group by type
    by_type: dict[str, list] = {}
    for d in duplicates:
        t = d["type"]
        by_type.setdefault(t, []).append(d)

    print("=" * 70)
    print("DUPLICATE DETECTION ANALYSIS")
    print("=" * 70)
    print(f"\nTotal candidates: {len(duplicates)}")
    for t, items in sorted(by_type.items()):
        print(f"  {t.upper()}: {len(items)}")

    # EXACT duplicates
    if "exact" in by_type:
        print("\n" + "─" * 70)
        print(f"🚨 EXACT DUPLICATES ({len(by_type['exact'])})")
        print("─" * 70)
        for d in by_type["exact"]:
            print(f"\n  [{d['similarity']:.3f}] {d['lemma1']}")
            print(f"           ↔ {d['lemma2']}")
            print(f"           File: {d.get('file1', 'N/A')}")

    # SUBSUMES
    if "subsumes" in by_type:
        print("\n" + "─" * 70)
        print(f"⚠️  SUBSUMPTION ({len(by_type['subsumes'])})")
        print("─" * 70)
        for d in by_type["subsumes"]:
            print(f"\n  [{d['similarity']:.3f}] {d['lemma1']}")
            print(f"           SUBSUMES {d['lemma2']}")
            print(f"           File: {d.get('file1', 'N/A')}")

    # SIMILAR patterns
    if "similar" in by_type:
        print("\n" + "─" * 70)
        print(f"🔄 SIMILAR PATTERNS ({len(by_type['similar'])})")
        print("─" * 70)

        patterns = categorize_similar_pairs(duplicates)

        for pattern_name, items in patterns.items():
            if items:
                nice_name = pattern_name.replace("_", " ").title()
                print(f"\n  {nice_name} ({len(items)} pairs):")
                for d in items[:3]:
                    print(f"    [{d['similarity']:.2f}] {d['lemma1']}")
                    print(f"           ↔ {d['lemma2']}")
                if len(items) > 3:
                    print(f"    ... and {len(items) - 3} more")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    exact_count = len(by_type.get("exact", []))
    subsumes_count = len(by_type.get("subsumes", []))
    similar_count = len(by_type.get("similar", []))

    if exact_count == 0:
        print("\n✅ No exact duplicates found.")
    else:
        print(f"\n🚨 {exact_count} exact duplicate(s) found - review for potential consolidation.")

    if subsumes_count > 0:
        print(f"⚠️  {subsumes_count} subsumption case(s) - review if stricter lemmas are needed.")

    if similar_count > 0:
        print(f"🔄 {similar_count} similar pattern(s) - likely intentional design variants.")


def print_markdown_report(data: dict, index_name: str = "index") -> None:
    """Print analysis as markdown."""
    duplicates = data["duplicates"]

    # Group by type
    by_type: dict[str, list] = {}
    for d in duplicates:
        t = d["type"]
        by_type.setdefault(t, []).append(d)

    print(f"# Duplicate Detection Analysis: {index_name}")
    print()
    print("## Summary")
    print()
    print("| Category | Count | Description |")
    print("|----------|-------|-------------|")
    print(f"| **EXACT** | {len(by_type.get('exact', []))} | Identical requires & ensures |")
    print(
        f"| **SUBSUMES** | {len(by_type.get('subsumes', []))} | Weaker preconditions, same postconditions |"
    )
    print(f"| **SIMILAR** | {len(by_type.get('similar', []))} | High semantic similarity |")
    print()

    # EXACT duplicates
    if "exact" in by_type:
        print("## Exact Duplicates")
        print()
        for d in by_type["exact"]:
            print(f"### `{d['lemma1']}` = `{d['lemma2']}`")
            print()
            print(f"- **Similarity**: {d['similarity']:.3f}")
            print(f"- **File**: {d.get('file1', 'N/A')}")
            print()

    # SUBSUMES
    if "subsumes" in by_type:
        print("## Subsumption Cases")
        print()
        for d in by_type["subsumes"]:
            print(f"### `{d['lemma1']}` SUBSUMES `{d['lemma2']}`")
            print()
            print(f"- **Similarity**: {d['similarity']:.3f}")
            print(f"- **File**: {d.get('file1', 'N/A')}")
            print()

    # SIMILAR patterns
    if "similar" in by_type:
        print("## Similar Patterns")
        print()

        patterns = categorize_similar_pairs(duplicates)

        print("| Pattern | Count |")
        print("|---------|-------|")
        for pattern_name, items in patterns.items():
            nice_name = pattern_name.replace("_", " ").title()
            print(f"| {nice_name} | {len(items)} |")
        print()

        for pattern_name, items in patterns.items():
            if items:
                nice_name = pattern_name.replace("_", " ").title()
                print(f"### {nice_name} ({len(items)} pairs)")
                print()
                for d in items[:5]:
                    print(f"- `{d['lemma1']}` ↔ `{d['lemma2']}` [{d['similarity']:.2f}]")
                if len(items) > 5:
                    print(f"- ... and {len(items) - 5} more")
                print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze duplicate detection results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/analyze_duplicates.py duplicates.json
  python scripts/analyze_duplicates.py duplicates.json --markdown > analysis.md
""",
    )
    parser.add_argument("json_file", help="Path to duplicate detection JSON output")
    parser.add_argument("--markdown", "-m", action="store_true", help="Output as markdown")
    parser.add_argument("--name", "-n", help="Name for the index (used in markdown header)")

    args = parser.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: File not found: {json_path}", file=sys.stderr)
        return 1

    try:
        with open(json_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1

    if "duplicates" not in data:
        print("Error: JSON does not contain 'duplicates' key", file=sys.stderr)
        return 1

    index_name = args.name or json_path.stem.replace("_duplicates", "")

    if args.markdown:
        print_markdown_report(data, index_name)
    else:
        print_text_report(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
