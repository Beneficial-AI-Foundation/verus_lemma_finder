#!/usr/bin/env python3
"""
Regression tests for query normalization and equivalence using pytest.

These tests ensure that semantically equivalent queries return the same or similar results,
particularly focusing on the improvements made to handle different variable names,
mathematical notation, and implication order.

Usage:
    pytest tests/test_regression.py -v
    pytest tests/test_regression.py -v -k "division"  # Run specific test
    python -m pytest tests/test_regression.py --index=your_index.json
"""

import sys
from pathlib import Path

# Add parent directory to path for src layout
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pytest
except ImportError:
    print("pytest not installed. Install with: uv pip install pytest")
    sys.exit(1)

from verus_lemma_finder import LemmaSearcher

# Test configuration
DEFAULT_INDEX = Path(__file__).parent.parent / "curve25519-dalek_lemma_index.json"
TOLERANCE_POSITIONS = 4  # Allow lemma to be within this many positions of expected


@pytest.fixture(scope="module")
def searcher(request):
    """Load the lemma searcher once for all tests"""
    index_path = Path(request.config.getoption("--index"))

    if not index_path.exists():
        pytest.skip(f"Index file not found: {index_path}")

    try:
        searcher = LemmaSearcher(index_path)
    except Exception as e:
        pytest.skip(f"Failed to load searcher: {e}")

    # Warn if embeddings not available
    if searcher.embeddings is None:
        print("\n⚠️  WARNING: Embeddings not available. Results may be less accurate.")
        print("   Regenerate index with --embeddings for best results.\n")

    return searcher


def check_lemma_position(
    searcher: LemmaSearcher,
    query: str,
    expected_lemma: str,
    expected_position: int = 0,
    tolerance: int = TOLERANCE_POSITIONS,
) -> tuple[bool, int, str]:
    """
    Check if expected lemma appears at the right position.

    Returns: (passed, actual_position, message)
    """
    results = searcher.fuzzy_search(query, top_k=10)

    # Find position of expected lemma
    actual_position = None
    for i, (lemma, _score) in enumerate(results):
        if lemma.name == expected_lemma:
            actual_position = i
            break

    if actual_position is None:
        return False, -1, f"Lemma '{expected_lemma}' not found in top 10 results"
    elif actual_position == expected_position:
        return True, actual_position, f"Found at expected position {actual_position}"
    elif actual_position <= expected_position + tolerance:
        return (
            True,
            actual_position,
            f"Found at position {actual_position} (within tolerance)",
        )
    else:
        return (
            False,
            actual_position,
            f"Found at position {actual_position}, expected {expected_position}",
        )


# ============================================================================
# Test Case 1: Division from Multiplication Inequality
# This is the primary test case from the user's original question
# ============================================================================


class TestDivisionFromMultiplication:
    """Test queries for: if a * b <= c then a <= c / b"""

    EXPECTED_LEMMA = "lemma_mul_le_implies_div_le"

    def test_query_with_words_forward_implication(self, searcher):
        """Query: if a times b <= c then a <= c div b"""
        query = "if a times b <= c then a <= c div b"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_query_with_operators_backward_implication(self, searcher):
        """Query: x <= z / y if x * y <= z and y > 0"""
        query = "x <= z / y if x * y <= z and y > 0"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_query_with_different_variables(self, searcher):
        """Query: if m * n <= p then m <= p / n"""
        query = "if m * n <= p then m <= p / n"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_query_with_when_keyword(self, searcher):
        """Query: a <= c / b when a mul b <= c"""
        query = "a <= c / b when a mul b <= c"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"


# ============================================================================
# Test Case 2: Multiplication Positivity
# ============================================================================


class TestMultiplicationPositivity:
    """Test queries for: if a > 0 and b > 0 then a * b > 0"""

    EXPECTED_LEMMA = "lemma_mul_strictly_positive"

    def test_forward_implication_with_operators(self, searcher):
        """Query: if a > 0 and b > 0 then a * b > 0"""
        query = "if a > 0 and b > 0 then a * b > 0"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_backward_implication_with_mul(self, searcher):
        """Query: a mul b > 0 if a > 0 and b > 0"""
        query = "a mul b > 0 if a > 0 and b > 0"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_natural_language_description(self, searcher):
        """Query: product is positive if both factors are positive"""
        query = "product is positive if both factors are positive"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"


# ============================================================================
# Test Case 3: Small Modular Arithmetic
# ============================================================================


class TestSmallModularArithmetic:
    """Test queries for: if x < m then x mod m = x"""

    EXPECTED_LEMMA = "lemma_small_mod"

    def test_backward_implication_with_mod(self, searcher):
        """Query: x mod m equals x when x < m (backward implication works better)"""
        query = "x mod m equals x when x < m"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_backward_implication_with_modulo(self, searcher):
        """Query: x modulo m equals x when x < m"""
        query = "x modulo m equals x when x < m"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_natural_language_description(self, searcher):
        """Query: small value mod is identity"""
        query = "small value mod is identity"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"


# ============================================================================
# Test Case 4: Division Bounds
# ============================================================================


class TestDivisionBounds:
    """Test queries for: if a < b * c then a / b < c"""

    # Note: lemma_multiply_divide_lt is the exact match for this pattern
    # (lemma_div_strictly_bounded has different variable ordering)
    EXPECTED_LEMMA = "lemma_multiply_divide_lt"

    def test_forward_implication_with_operators(self, searcher):
        """Query: if a < b * c then a / b < c"""
        query = "if a < b * c then a / b < c"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_backward_implication_with_div_mul(self, searcher):
        """Query: a div b < c when a < b mul c"""
        query = "a div b < c when a < b mul c"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"

    def test_operator_only_style(self, searcher):
        """Query: a / b < c if a < b * c"""
        query = "a / b < c if a < b * c"
        passed, pos, msg = check_lemma_position(searcher, query, self.EXPECTED_LEMMA)
        assert passed, f"{msg}\nQuery: {query}"


# ============================================================================
# Utility: Check if lemma exists
# ============================================================================


@pytest.mark.parametrize(
    "lemma_name",
    [
        "lemma_mul_le_implies_div_le",
        "lemma_mul_strictly_positive",
        "lemma_small_mod",
        "lemma_multiply_divide_lt",  # Changed from lemma_div_strictly_bounded
    ],
)
def test_expected_lemmas_exist(searcher, lemma_name):
    """Verify that all expected lemmas exist in the index"""
    exists = any(lemma.name == lemma_name for lemma in searcher.lemmas)
    assert exists, (
        f"Expected lemma '{lemma_name}' not found in index. Check your SCIP indexing."
    )


# ============================================================================
# Main: Allow running without pytest
# ============================================================================

if __name__ == "__main__":
    # Allow running directly without pytest
    print("This test file is designed to be run with pytest.")
    print("\nUsage:")
    print("  pytest tests/test_regression.py -v")
    print("  pytest tests/test_regression.py --index=your_index.json -v")
    print("\nTo install pytest:")
    print("  pip install pytest")
    print("\nOr run with python -m pytest:")
    print("  python -m pytest tests/test_regression.py -v")
