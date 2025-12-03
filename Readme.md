# Verus Lemma Finder

Semantic search for Verus lemmas. Find lemmas using natural language queries.

## ✨ Highlights

- **Semantic search** - find lemmas by meaning, not just keywords
- **Proper Verus parsing** with `verus_syn` - accurate `requires`/`ensures`/`decreases` extraction
- **Web interface** for easy exploration
- **Query normalization** - variable names and math operators are normalized

## Quick Start

```bash
git clone https://github.com/Beneficial-AI-Foundation/verus_lemma_finder.git
cd verus_lemma_finder
uv sync --extra dev

# Build Rust parser for accurate Verus parsing (requires Rust toolchain)
uv run maturin develop --release
```

### Web Demo

```bash
./demo/start_demo.sh
```

Open http://localhost:8000 and search!

**Included indexes** (in `data/`):
- `vstd_lemma_index.json` - Verus standard library 
- `curve25519-dalek_lemma_index.json` - [curve25519-dalek](https://github.com/Beneficial-AI-Foundation/dalek-lite)

### CLI Search

```bash
# Search by natural language
uv run python -m verus_lemma_finder search "dividing both sides preserves inequality" data/vstd_lemma_index.json

# Find lemmas similar to a known lemma
uv run python -m verus_lemma_finder similar lemma_mod_adds data/vstd_lemma_index.json

# Interactive mode
uv run python -m verus_lemma_finder interactive data/vstd_lemma_index.json
```

### Python API

```python
from verus_lemma_finder import get_similar_lemmas, get_similar_to_lemma

# Search by query
results = get_similar_lemmas("modulo bounds", index_path="data/vstd_lemma_index.json")

# Find lemmas similar to a known lemma
results = get_similar_to_lemma("lemma_mod_adds", index_path="data/vstd_lemma_index.json")
```

## Add Your Own Project

```bash
# Interactive (recommended)
uv run python scripts/add_index.py

# Or one command
uv run python scripts/add_index.py --name myproject --path /path/to/project
```

This generates SCIP, builds the index, and configures the demo server.

## Documentation

| Topic | Link |
|-------|------|
| **Full Usage Guide** | [`docs/usage.md`](docs/usage.md) |
| **Python API** | [`docs/api.md`](docs/api.md) |
| Web Demo | [`demo/quickstart.md`](demo/quickstart.md) |
| Installation | [`docs/install.md`](docs/install.md) |
| Rust Parser | [`docs/rust-parser.md`](docs/rust-parser.md) |
| Architecture | [`docs/lemma-search-design.md`](docs/lemma-search-design.md) |

## Example Queries

**Natural language** - describe what you need:
```bash
uv run python -m verus_lemma_finder search "modulo is always less than divisor" data/vstd_lemma_index.json
# → lemma_mod_bound: 0 <= x % m < m

uv run python -m verus_lemma_finder search "multiplication preserves inequality" data/vstd_lemma_index.json
# → lemma_mul_inequality: x < y && z > 0 ==> x * z < y * z
```

**Math notation** - variable names are normalized automatically:
```bash
uv run python -m verus_lemma_finder search "a * b <= c implies a <= c / b" data/vstd_lemma_index.json
# Same results as: "x * y <= z implies x <= z / y"
```

## Requirements

- Python 3.12+
- `uv` (recommended) or pip
- Rust toolchain (for accurate Verus parsing)

**For building your own indexes:**
- `verus-analyzer` + `scip` CLI

## Built With

- [sentence-transformers](https://www.sbert.net/) - semantic embeddings
- [verus_syn](https://crates.io/crates/verus_syn) - accurate Verus parsing
- [PyO3](https://pyo3.rs/) - Rust-Python bindings

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  🦀 Rust (verus_syn)          │  🐍 Python                  │
│  ─────────────────────────────│─────────────────────────────│
│  • Accurate Verus parsing     │  • Semantic embeddings      │
│  • AST traversal              │  • sentence-transformers    │
│  • Spec extraction            │  • CLI & Web interface      │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT
