# Verus Lemma Finder

Semantic search for Verus lemmas and specifications. Find lemmas in your project and vstd using natural language queries.

## Features

- Semantic search using sentence transformers
- Query normalization (variables, operators, implication order)
- vstd integration
- Interactive mode
- Built on SCIP from verus-analyzer

Query normalization example:
```bash
# These queries match the same lemmas:
"if a times b <= c then a <= c div b"
"x <= z / y if x * y <= z"
"if m * n <= p then m <= p / n"
```

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
pip install -e ".[dev]"  # with dev dependencies
```

See [`docs/install.md`](docs/install.md) for detailed installation instructions.

## Usage

### Index your project

```bash
# Generate SCIP from your Verus project
cd /path/to/your/project
verus-analyzer scip .
scip print --json index.scip > project_scip.json

# Build searchable index
verus-lemma-finder index project_scip.json -o lemma_index.json --embeddings
```

### Search

```bash
# Basic search
verus-lemma-finder search "division properties" lemma_index.json

# Interactive mode
verus-lemma-finder interactive lemma_index.json

# With uv
uv run verus-lemma-finder search "your query" lemma_index.json
```

### vstd integration

```bash
# Setup vstd (one-time)
verus-lemma-finder setup-vstd ./verus
verus-lemma-finder generate-scip ./verus

# Add to your index
verus-lemma-finder add-vstd ./verus/verus_scip.json lemma_index.json

# Search both project and vstd
verus-lemma-finder search "division properties" lemma_index.json
```

### Generate SCIP automatically

```bash
# Generate SCIP for a project automatically
verus-lemma-finder generate-scip /path/to/project

# Then index it
verus-lemma-finder index /path/to/project/project_scip.json --embeddings
```

## Documentation

See [`docs/`](docs/) for detailed documentation:
- Installation: [`install.md`](docs/install.md)
- Architecture: [`lemma-search-design.md`](docs/lemma-search-design.md)
- Configuration: [`configuration.md`](docs/configuration.md)
- Testing: [`testing.md`](docs/testing.md)
- Search tips: [`search-tips.md`](docs/search-tips.md)
- vstd integration: [`vstd-integration-guide.md`](docs/vstd-integration-guide.md)

## Project Structure

```
verus_lemma_finder/
├── src/verus_lemma_finder/      # Main package
│   ├── cli.py                   # CLI entry point
│   ├── indexing.py              # Index building
│   ├── search.py                # Search functionality
│   ├── normalization.py         # Query normalization
│   ├── extraction.py            # Spec extraction
│   ├── models.py                # Data models
│   ├── config.py                # Configuration
│   └── scip_utils.py            # SCIP utilities
├── tests/                       # Test suite
├── docs/                        # Documentation
└── pyproject.toml               # Project config
```

## Requirements

- Python 3.12+
- `verus-analyzer` (from Verus installation)
- `scip` CLI tool (https://github.com/sourcegraph/scip)
- `sentence-transformers` (installed automatically)

## Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_regression.py::TestDivisionFromMultiplication -v
```

See [`docs/testing.md`](docs/testing.md) for details.

