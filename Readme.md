# Verus Lemma Finder

Semantic search for Verus lemmas and specifications. Find lemmas in your project and vstd using natural language queries.

## ✨ Highlights

- **Semantic search** using sentence transformers - find lemmas by meaning, not just keywords
- **Proper Verus parsing** with `verus_syn` - accurate extraction of `requires`, `ensures`, `decreases`
- **Web interface** for easy exploration
- **Query normalization** - handles variable names, operators, implication order
- **vstd integration** - search both your project and the standard library

## 🌐 Try the Web Demo!

**Want to try it without installing anything?** Check out our web interface:

```bash
# Clone and run the demo (no verus-analyzer or scip needed!)
git clone https://github.com/your-org/verus-lemma-finder
cd verus-lemma-finder
./demo/start_demo.sh
```

Then open http://localhost:8000 in your browser!

**Note**: The demo uses pre-built index files. You only need `verus-analyzer` and `scip` if you want to build your own indexes from Verus source code.

---

## Features

- **Semantic search** using sentence transformers (all-MiniLM-L6-v2)
- **Accurate Verus parsing** with [`verus_syn`](https://crates.io/crates/verus_syn) - handles all Verus syntax:
  - `requires`, `ensures`, `decreases` clauses
  - Quantifiers: `forall|x|`, `exists|x|`
  - Operators: `==>`, `&&&`, `|||`, `=~=`
  - Functions inside `verus!` macros (including inside `impl` blocks)
- **Web interface** for easy exploration
- **Query normalization** (variables, operators, implication order)
- **vstd integration**
- **Interactive mode**
- Built on SCIP from verus-analyzer

Query normalization example:
```bash
# These queries match the same lemmas:
"if a times b <= c then a <= c div b"
"x <= z / y if x * y <= z"
"if m * n <= p then m <= p / n"
```

## Installation

### Quick Install (pre-built wheels)

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
pip install -e ".[dev]"  # with dev dependencies
```

### Building with Rust Parser (recommended for best accuracy)

The Rust parser provides accurate extraction of Verus specifications using `verus_syn`:

```bash
# Install maturin
pip install maturin

# Build and install with Rust parser
maturin develop --release

# Or using uvx
uvx maturin develop --release
```

This enables proper parsing of:
- `requires`, `ensures`, `decreases` clauses
- Complex Verus syntax (`forall|x|`, `==>`, `&&&`)
- Functions inside `verus!` macros (including in `impl` blocks)

See [`docs/install.md`](docs/install.md) and [`docs/rust-parser.md`](docs/rust-parser.md) for details.

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
- **Web Demo**: [`demo/QUICKSTART.md`](demo/QUICKSTART.md) - Start the web interface
- **Deployment**: [`demo/DEPLOYMENT.md`](demo/DEPLOYMENT.md) - Share with others
- **Rust Parser**: [`docs/rust-parser.md`](docs/rust-parser.md) - Building and using the verus_syn parser
- Installation: [`docs/install.md`](docs/install.md)
- Architecture: [`docs/lemma-search-design.md`](docs/lemma-search-design.md)
- Configuration: [`docs/configuration.md`](docs/configuration.md)
- Testing: [`docs/testing.md`](docs/testing.md)
- Search tips: [`docs/search-tips.md`](docs/search-tips.md)
- vstd integration: [`docs/vstd-integration-guide.md`](docs/vstd-integration-guide.md)

## Project Structure

```
verus_lemma_finder/
├── src/verus_lemma_finder/      # Main Python package
│   ├── cli.py                   # CLI entry point
│   ├── indexing.py              # Index building
│   ├── search.py                # Search functionality
│   ├── normalization.py         # Query normalization
│   ├── extraction.py            # Spec extraction (calls Rust parser)
│   ├── models.py                # Data models
│   ├── config.py                # Configuration
│   └── scip_utils.py            # SCIP utilities
├── rust/                        # Rust parser (verus_syn + PyO3)
│   ├── Cargo.toml               # Rust dependencies
│   └── src/lib.rs               # PyO3 bindings for verus_syn
├── tests/                       # Test suite
├── docs/                        # Documentation
├── demo/                        # Web demo
└── pyproject.toml               # Project config (maturin build)
```

## Requirements

- Python 3.12+
- `verus-analyzer` (https://github.com/verus-lang/verus-analyzer)
- `scip` CLI tool (https://github.com/sourcegraph/scip)
- `sentence-transformers` (installed automatically)

### Optional (for building from source)

- Rust toolchain (for building the `verus_parser` module)
- `maturin` (Python/Rust build tool)

## Architecture

This project uses a **hybrid Rust + Python** approach for best of both worlds:

```
┌─────────────────────────────────────────────────────────────┐
│                    Verus Lemma Finder                       │
├─────────────────────────────────────────────────────────────┤
│  🦀 Rust (verus_syn)          │  🐍 Python                  │
│  ─────────────────────────────│─────────────────────────────│
│  • Accurate Verus parsing     │  • Semantic embeddings      │
│  • AST traversal              │  • sentence-transformers    │
│  • Spec extraction            │  • Search algorithms        │
│  • PyO3 bindings              │  • CLI & Web interface      │
└─────────────────────────────────────────────────────────────┘
```

- **Rust + verus_syn**: Proper parsing of Verus syntax (no regex hacks!)
- **Python + sentence-transformers**: Powerful semantic search with embeddings

## Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_regression.py::TestDivisionFromMultiplication -v

# Test Rust parser
cd rust && cargo test
```

See [`docs/testing.md`](docs/testing.md) for details.

