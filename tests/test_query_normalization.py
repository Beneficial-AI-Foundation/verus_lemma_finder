#!/usr/bin/env python3
"""
Demo script to show query normalization improvements.

This demonstrates how the enhanced normalization helps match semantically
equivalent queries with different syntax.
"""

import sys
from pathlib import Path

# Add parent directory to path for src layout
sys.path.insert(0, str(Path(__file__).parent.parent))

from verus_lemma_finder import LemmaSearcher


def test_normalization():
    """Test the normalization improvements"""

    # Create a bare searcher just for testing normalization
    searcher = LemmaSearcher.__new__(LemmaSearcher)
    searcher.lemmas = []
    searcher.embeddings = None

    print("=" * 80)
    print("QUERY NORMALIZATION IMPROVEMENTS")
    print("=" * 80)
    print()

    # Test cases showing semantically equivalent queries
    test_cases = [
        (
            "if a times b <= c then a <= c div b",
            "x <= z / y if x * y <= z and y > 0",
            "Should match: Different variables and operators, different order",
        ),
        (
            "if x + y = z then x = z - y",
            "x = z - y if x + y = z",
            "Should match: Same query, different implication order",
        ),
        ("a multiply b equals c", "a * b = c", "Should match: Word form vs operator"),
    ]

    for i, (query1, query2, description) in enumerate(test_cases, 1):
        print(f"Test Case {i}: {description}")
        print("-" * 80)
        print(f"Query 1: {query1}")
        print(f"Query 2: {query2}")
        print()

        # Normalize both queries
        norm1 = searcher._normalize_math_query(query1)
        norm2 = searcher._normalize_math_query(query2)

        print(f"Normalized 1: {norm1}")
        print(f"Normalized 2: {norm2}")
        print()

        # Generate variations
        vars1 = searcher._generate_query_variations(norm1)
        vars2 = searcher._generate_query_variations(norm2)

        print("Variations of Query 1:")
        for j, v in enumerate(vars1, 1):
            print(f"  {j}. {v}")
        print()

        print("Variations of Query 2:")
        for j, v in enumerate(vars2, 1):
            print(f"  {j}. {v}")
        print()

        # Check for matches
        matches = []
        for v1 in vars1:
            for v2 in vars2:
                if v1 == v2:
                    matches.append(v1)

        if matches:
            print("✅ EXACT MATCHES FOUND:")
            for match in matches:
                print(f"   - {match}")
        else:
            # Calculate similarity
            print("❓ No exact match, but normalized forms are similar:")
            print("   Similarity will be detected by semantic embeddings")

        print()
        print("=" * 80)
        print()


def test_real_search(index_file: Path):
    """Test real search with the two queries from the user's example"""

    if not index_file.exists():
        print(f"❌ Index file not found: {index_file}")
        print("   Run this first to generate an index with embeddings")
        return

    print("=" * 80)
    print("REAL SEARCH COMPARISON")
    print("=" * 80)
    print()

    searcher = LemmaSearcher(index_file)

    query1 = "if a times b <= c then a <= c div b"
    query2 = "x <= z / y if x * y <= z and y > 0"

    print(f"Query 1: {query1}")
    print()
    results1 = searcher.fuzzy_search(query1, top_k=5)

    if results1:
        print(f"Top {len(results1)} results:")
        for i, (lemma, score) in enumerate(results1, 1):
            print(f"  [{i}] {lemma.name} (score: {score:.3f})")
    else:
        print("  No results found")

    print()
    print("-" * 80)
    print()

    print(f"Query 2: {query2}")
    print()
    results2 = searcher.fuzzy_search(query2, top_k=5)

    if results2:
        print(f"Top {len(results2)} results:")
        for i, (lemma, score) in enumerate(results2, 1):
            print(f"  [{i}] {lemma.name} (score: {score:.3f})")
    else:
        print("  No results found")

    print()
    print("-" * 80)
    print()

    # Compare top results
    if results1 and results2:
        top_lemmas1 = {lemma.name for lemma, _ in results1[:3]}
        top_lemmas2 = {lemma.name for lemma, _ in results2[:3]}

        overlap = top_lemmas1 & top_lemmas2

        print("COMPARISON:")
        print(f"  Top 3 lemmas in Query 1: {', '.join(sorted(top_lemmas1))}")
        print(f"  Top 3 lemmas in Query 2: {', '.join(sorted(top_lemmas2))}")
        print(f"  Overlap: {len(overlap)}/{min(3, len(results1), len(results2))}")

        if overlap:
            print(f"  ✅ Common results: {', '.join(sorted(overlap))}")
        else:
            print("  ⚠️  No overlap in top 3 results")
            print("     This might indicate the index needs to be regenerated")
            print("     with the new normalization improvements.")

    print()
    print("=" * 80)


def main():
    """Main entry point"""
    print()

    # Test normalization
    test_normalization()

    # Test real search if index file provided
    if len(sys.argv) > 1:
        index_file = Path(sys.argv[1])
        test_real_search(index_file)
        print()
        print("NOTE: For best results, regenerate your index with the new code:")
        print("  python lemma_search_tool.py index <scip_file> --embeddings")
    else:
        print("To test with real lemma index, run:")
        print("  python test_query_normalization.py <path_to_lemma_index.json>")
        print()


if __name__ == "__main__":
    main()
