#!/usr/bin/env python3
"""
Regression tests for query normalization and equivalence.

Tests that semantically equivalent queries return the same or similar results,
particularly focusing on the improvements made to handle different variable names,
mathematical notation, and implication order.
"""

import sys
from pathlib import Path

# Add parent directory to path for src layout
sys.path.insert(0, str(Path(__file__).parent.parent))

from verus_lemma_finder import LemmaSearcher


class TestCase:
    """A test case for query equivalence"""

    def __init__(
        self, name: str, queries: list[str], expected_lemma: str, position: int = 0
    ):
        self.name = name
        self.queries = queries
        self.expected_lemma = expected_lemma
        self.position = position  # Expected position (0 = first result)

    def __str__(self):
        return f"TestCase({self.name})"


# Define regression test cases
REGRESSION_TESTS = [
    TestCase(
        name="Division from Multiplication Inequality",
        queries=[
            "if a times b <= c then a <= c div b",
            "x <= z / y if x * y <= z and y > 0",
            "if m * n <= p then m <= p / n",
            "a <= c / b when a mul b <= c",
        ],
        expected_lemma="lemma_mul_le_implies_div_le",
        position=0,  # Should be first result
    ),
    TestCase(
        name="Multiplication Positivity",
        queries=[
            "if a > 0 and b > 0 then a * b > 0",
            "a mul b > 0 if a > 0 and b > 0",
            "product is positive if both factors are positive",
        ],
        expected_lemma="lemma_mul_strictly_positive",
        position=0,
    ),
    TestCase(
        name="Small Modular Arithmetic",
        queries=[
            "if x < m then x mod m = x",
            "x modulo m equals x when x < m",
            "small value mod is identity",
        ],
        expected_lemma="lemma_small_mod",
        position=0,
    ),
    TestCase(
        name="Division Bounds",
        queries=[
            "if a < b * c then a / b < c",
            "a div b < c when a < b mul c",
            "a / b < c if a < b * c",
        ],
        expected_lemma="lemma_div_strictly_bounded",
        position=0,
    ),
]


class TestResult:
    """Result of running a test"""

    def __init__(
        self,
        test_case: TestCase,
        query: str,
        passed: bool,
        actual_position: int | None = None,
        message: str = "",
    ):
        self.test_case = test_case
        self.query = query
        self.passed = passed
        self.actual_position = actual_position
        self.message = message


def run_test_case(
    searcher: LemmaSearcher, test_case: TestCase, verbose: bool = False
) -> list[TestResult]:
    """
    Run a single test case with all its query variations.

    Returns a list of TestResult objects, one per query.
    """
    results = []

    # Check if expected lemma exists in index
    lemma_exists = any(lemma.name == test_case.expected_lemma for lemma in searcher.lemmas)

    if verbose:
        print(f"\n{'=' * 80}")
        print(f"Test: {test_case.name}")
        print(
            f"Expected: '{test_case.expected_lemma}' at position {test_case.position}"
        )
        if not lemma_exists:
            print("⚠️  WARNING: Expected lemma not found in index!")
        print(f"{'=' * 80}")

    for query in test_case.queries:
        if verbose:
            print(f'\nQuery: "{query}"')

        # Search with the query
        search_results = searcher.fuzzy_search(query, top_k=10)

        # Check if expected lemma is in results
        found_position = None
        for i, (lemma, _score) in enumerate(search_results):
            if lemma.name == test_case.expected_lemma:
                found_position = i
                break

        # Determine if test passed
        if found_position is None:
            passed = False
            message = f"❌ Expected lemma '{test_case.expected_lemma}' not found in top 10 results"
        elif found_position == test_case.position:
            passed = True
            message = f"✅ Found at expected position {found_position}"
        elif found_position <= test_case.position + 2:  # Allow some tolerance
            passed = True
            message = f"⚠️  Found at position {found_position} (expected {test_case.position}, within tolerance)"
        else:
            passed = False
            message = (
                f"❌ Found at position {found_position}, expected {test_case.position}"
            )

        if verbose:
            print(f"   {message}")
            if search_results:
                print("   Top 5 results:")
                for i, (lemma, score) in enumerate(search_results[:5]):
                    marker = "👉" if i == found_position else "  "
                    print(f"   {marker} [{i}] {lemma.name} (score: {score:.3f})")

        results.append(
            TestResult(
                test_case=test_case,
                query=query,
                passed=passed,
                actual_position=found_position,
                message=message,
            )
        )

    return results


def run_all_tests(
    index_file: Path, verbose: bool = False
) -> tuple[int, int, list[TestResult]]:
    """
    Run all regression tests.

    Returns: (passed_count, total_count, all_results)
    """
    print(f"\n{'=' * 80}")
    print("LEMMA SEARCH REGRESSION TESTS")
    print(f"{'=' * 80}")
    print(f"Index file: {index_file}")

    # Load searcher
    try:
        searcher = LemmaSearcher(index_file)
    except Exception as e:
        print(f"\n❌ Failed to load index: {e}")
        return 0, 0, []

    # Check if embeddings are available
    if searcher.embeddings is None:
        print("\n⚠️  WARNING: Embeddings not available. Results may be less accurate.")
        print("   Regenerate index with --embeddings for best results.")

    # Run all tests
    all_results = []
    for test_case in REGRESSION_TESTS:
        test_results = run_test_case(searcher, test_case, verbose=verbose)
        all_results.extend(test_results)

    # Calculate statistics
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)

    return passed, total, all_results


def print_summary(passed: int, total: int, all_results: list[TestResult]):
    """Print test summary"""
    print(f"\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")

    # Group by test case
    by_test_case = {}
    for result in all_results:
        test_name = result.test_case.name
        if test_name not in by_test_case:
            by_test_case[test_name] = []
        by_test_case[test_name].append(result)

    # Print results by test case
    for test_name, results in by_test_case.items():
        test_passed = sum(1 for r in results if r.passed)
        test_total = len(results)
        status = "✅ PASS" if test_passed == test_total else "❌ FAIL"

        print(f"\n{status} {test_name} ({test_passed}/{test_total})")

        # Show failed queries
        failed = [r for r in results if not r.passed]
        if failed:
            for result in failed:
                print(f'  ❌ "{result.query}"')
                print(f"     {result.message}")

    # Overall summary
    print(f"\n{'=' * 80}")
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"OVERALL: {passed}/{total} queries passed ({percentage:.1f}%)")
    print(f"{'=' * 80}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("\nPossible fixes:")
        print("  1. Regenerate index with latest code and --embeddings")
        print("  2. Ensure sentence-transformers is installed")
        print("  3. Check that the expected lemmas exist in your index")
        return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run regression tests for query normalization"
    )
    parser.add_argument(
        "index_file", type=Path, nargs="?", help="Path to lemma index file"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output for each query",
    )
    parser.add_argument(
        "--list-tests", action="store_true", help="List all test cases and exit"
    )

    args = parser.parse_args()

    # List tests if requested
    if args.list_tests:
        print("Available test cases:")
        for i, test in enumerate(REGRESSION_TESTS, 1):
            print(f"\n{i}. {test.name}")
            print(f"   Expected lemma: {test.expected_lemma}")
            print("   Test queries:")
            for query in test.queries:
                print(f'     - "{query}"')
        return 0

    # Check if index file was provided
    if not args.index_file:
        print("❌ Error: index_file is required")
        parser.print_help()
        return 1

    # Check if index exists
    if not args.index_file.exists():
        print(f"❌ Error: Index file not found: {args.index_file}")
        print("\nGenerate an index first:")
        print("  python lemma_search_tool.py index <scip_file> --embeddings")
        return 1

    # Run tests
    passed, total, all_results = run_all_tests(args.index_file, verbose=args.verbose)

    if total == 0:
        print("\n❌ No tests were run")
        return 1

    # Print summary
    return print_summary(passed, total, all_results)


if __name__ == "__main__":
    sys.exit(main())
