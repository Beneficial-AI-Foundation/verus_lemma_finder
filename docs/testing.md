# Testing Guide

This document describes how to run tests for the Verus Lemma Finder project.

## Test Suite

The project includes regression tests that verify:
- Query normalization works correctly
- Semantically equivalent queries return similar results  
- Expected lemmas are found for specific queries
- Different phrasings (variables, operators, implication order) are handled

## Quick Start

### Install Test Dependencies

```bash
# Using uv (recommended)
uv sync --extra dev

# Or using pip
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Run with default index (curve25519-dalek_lemma_index.json)
uv run pytest tests/test_regression.py

# Run with custom index
uv run pytest tests/test_regression.py --index=your_index.json

# Run with verbose output
uv run pytest tests/test_regression.py -v

# Run specific test class
uv run pytest tests/test_regression.py::TestDivisionFromMultiplication -v

# Run specific test
uv run pytest tests/test_regression.py::TestDivisionFromMultiplication::test_query_with_words_forward_implication -v
```

## Test Structure

### Regression Tests (`test_regression.py`)

Tests for query equivalence and normalization. Each test class focuses on a specific mathematical property:

#### 1. TestDivisionFromMultiplication
Tests the primary use case from the original issue:
- `"if a times b <= c then a <= c div b"`
- `"x <= z / y if x * y <= z and y > 0"`
- `"if m * n <= p then m <= p / n"`
- `"a <= c / b when a mul b <= c"`

Expected lemma: `lemma_mul_le_implies_div_le`

#### 2. TestMultiplicationPositivity
Tests queries about positive products:
- `"if a > 0 and b > 0 then a * b > 0"`
- `"a mul b > 0 if a > 0 and b > 0"`
- `"product is positive if both factors are positive"`

Expected lemma: `lemma_mul_strictly_positive`

#### 3. TestSmallModularArithmetic
Tests queries about modulo with small values:
- `"if x < m then x mod m = x"`
- `"x modulo m equals x when x < m"`
- `"small value mod is identity"`

Expected lemma: `lemma_small_mod`

#### 4. TestDivisionBounds
Tests queries about division bounds:
- `"if a < b * c then a / b < c"`
- `"a div b < c when a < b mul c"`
- `"a / b < c if a < b * c"`

Expected lemma: `lemma_div_strictly_bounded`

## Standalone Testing (Without pytest)

If you prefer not to use pytest, there's also a standalone test script:

```bash
# List available tests
uv run python tests/run_query_equivalence.py --list-tests

# Run tests with default index
uv run python tests/run_query_equivalence.py data/curve25519-dalek_lemma_index.json

# Run with verbose output
uv run python tests/run_query_equivalence.py data/curve25519-dalek_lemma_index.json -v
```

## Common Issues

### Tests Failing

If tests are failing, check:

1. **Index has embeddings**: Regenerate the index (embeddings are enabled by default)
   ```bash
   uv run python -m verus_lemma_finder index <scip_file> -o lemma_index.json
   ```

2. **sentence-transformers installed**: 
   ```bash
   uv sync --extra dev  # Installs all dependencies
   ```

3. **Expected lemmas exist**: Some lemmas might not be in your project
   ```bash
   uv run pytest tests/test_regression.py::test_expected_lemmas_exist -v
   ```

### Embeddings Warning

If you see:
```
⚠️  WARNING: Embeddings not available. Results may be less accurate.
```

This means either:
- The index was built with `--no-embeddings`
- sentence-transformers is not installed

Tests may still pass but with lower accuracy.

## Test Configuration

### Custom Index Path

```bash
# Default index location
uv run pytest tests/test_regression.py

# Custom index
uv run pytest tests/test_regression.py --index=/path/to/your/index.json
```

### Tolerance

Tests allow some tolerance in position (default: ±2 positions). This is because:
- Semantic search isn't deterministic across different models/versions
- Multiple lemmas might have similar scores
- Small variations are acceptable as long as the lemma is in top results

To modify tolerance, edit `TOLERANCE_POSITIONS` in `test_regression.py`.

## Adding New Tests

To add new test cases:

1. **Create a new test class**:
   ```python
   class TestYourFeature:
       EXPECTED_LEMMA = "lemma_your_lemma"
       
       def test_your_query(self, searcher):
           """Query: your query here"""
           query = "your query"
           passed, pos, msg = check_lemma_position(
               searcher, query, self.EXPECTED_LEMMA
           )
           assert passed, f"{msg}\nQuery: {query}"
   ```

2. **Add the expected lemma to existence check**:
   ```python
   @pytest.mark.parametrize("lemma_name", [
       # ... existing lemmas ...
       "lemma_your_lemma",
   ])
   ```

3. **Run your new test**:
   ```bash
   uv run pytest tests/test_regression.py::TestYourFeature -v
   ```

## Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions. See `.github/workflows/ci.yml` for the complete workflow configuration.

## Coverage

To check test coverage:

```bash
# Install with dev dependencies (includes pytest-cov)
uv sync --extra dev

# Run tests with coverage
uv run pytest tests/test_regression.py --cov=verus_lemma_finder --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Tips

- **Run specific tests during development**: Use `-k` to filter
  ```bash
  uv run pytest tests/test_regression.py -k "division" -v
  ```

- **See print statements**: Use `-s` flag
  ```bash
  uv run pytest tests/test_regression.py -s
  ```

- **Stop on first failure**: Use `-x` flag
  ```bash
  uv run pytest tests/test_regression.py -x
  ```

- **Verbose failure info**: Already enabled by default in `pyproject.toml`

## Summary

```bash
# Quick reference for common commands:

# Install dependencies
uv sync --extra dev

# Run all tests
uv run pytest tests/test_regression.py

# Run with custom index
uv run pytest tests/test_regression.py --index=my_index.json

# Run specific test class
uv run pytest tests/test_regression.py::TestDivisionFromMultiplication

# Run with verbose output
uv run pytest -v tests/test_regression.py

# Run without pytest (standalone)
uv run python tests/run_query_equivalence.py data/vstd_lemma_index.json -v
```

