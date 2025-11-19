#!/usr/bin/env python3
"""
Basic search tests - simple smoke tests for the lemma search tool.

Usage:
    python tests/test_basic_search.py [index_file]
"""

import sys
from pathlib import Path

# Add parent directory to path for src layout
sys.path.insert(0, str(Path(__file__).parent.parent))

from verus_lemma_finder import LemmaSearcher


def run_basic_tests(index_file: Path):
    """Run basic search tests"""

    print("=" * 80)
    print("BASIC LEMMA SEARCH TESTS")
    print("=" * 80)
    print(f"Index: {index_file}\n")

    try:
        searcher = LemmaSearcher(index_file)
    except Exception as e:
        print(f"❌ Failed to load index: {e}")
        return 1

    test_queries = [
        ("Multiplication/Division lemma", "if a times b <= c then a <= c div b", 3),
        ("Modulo properties", "modulo preserves order", 3),
        ("Byte extraction", "extract byte from number", 3),
    ]

    all_passed = True

    for test_name, query, top_k in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Test: {test_name}")
        print(f"{'=' * 80}")
        print(f'Query: "{query}"')
        print()

        try:
            results = searcher.fuzzy_search(query, top_k=top_k)

            if not results:
                print("❌ No results found")
                all_passed = False
                continue

            print(f"✅ Found {len(results)} results:\n")

            for i, (lemma, score) in enumerate(results, 1):
                print(f"[{i}] {lemma.name} (score: {score:.3f})")
                print(f"    {lemma.file_path}:{lemma.line_number}")
                if lemma.documentation:
                    print(f"    {lemma.documentation}")
                print()

        except Exception as e:
            print(f"❌ Error during search: {e}")
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("✅ All tests completed successfully")
        return 0
    else:
        print("⚠️  Some tests had issues")
        return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run basic lemma search tests")
    parser.add_argument(
        "index_file",
        nargs="?",
        type=Path,
        default=Path("lemma_index.json"),
        help="Path to lemma index file (default: lemma_index.json)",
    )

    args = parser.parse_args()

    if not args.index_file.exists():
        print(f"❌ Error: Index file not found: {args.index_file}")
        print("\nGenerate an index first:")
        print("  python lemma_search_tool.py index <scip_file> --embeddings")
        return 1

    return run_basic_tests(args.index_file)


if __name__ == "__main__":
    sys.exit(main())
