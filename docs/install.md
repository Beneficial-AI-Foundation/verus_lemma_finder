# Installation Guide

## Quick Install

### From Source (Recommended)

```bash
git clone https://github.com/Beneficial-AI-Foundation/verus_lemma_finder.git
cd verus_lemma_finder
uv sync --extra dev

# Build Rust parser for accurate Verus parsing (requires Rust toolchain)
uv run maturin develop --release
```

### From GitHub Release

Download the wheel from [GitHub Releases](https://github.com/Beneficial-AI-Foundation/verus_lemma_finder/releases):

```bash
# Download and install the wheel for your platform
pip install verus_lemma_finder-X.Y.Z-cp312-cp312-linux_x86_64.whl
```

That's it! You can now:
- Run the web demo: `./demo/start_demo.sh`
- Search from CLI: `uv run python -m verus_lemma_finder search "query" data/vstd_lemma_index.json`

## Prerequisites

### Required

| Tool | Version | Check | Purpose |
|------|---------|-------|---------|
| Python | 3.12+ | `python3 --version` | Runtime |
| uv | any | `uv --version` | Package management |

### For Building Your Own Indexes

| Tool | Check | Purpose |
|------|-------|---------|
| verus-analyzer | `verus-analyzer --version` | Generate SCIP from Verus code |
| scip | `scip --version` | Convert SCIP to JSON |

**Install verus-analyzer:** https://github.com/verus-lang/verus-analyzer

**Install scip:** https://github.com/sourcegraph/scip/releases

### For Best Parsing Accuracy (Optional)

| Tool | Check | Purpose |
|------|-------|---------|
| Rust | `rustc --version` | Build verus_syn parser |
| maturin | `maturin --version` | Python-Rust bridge |

## Installation Methods

### Method 1: uv (Recommended)

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/Beneficial-AI-Foundation/verus_lemma_finder.git
cd verus_lemma_finder
uv sync
```

### Method 2: pip

```bash
git clone https://github.com/Beneficial-AI-Foundation/verus_lemma_finder.git
cd verus_lemma_finder

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Rust Parser

The Rust parser is built automatically in the Quick Install steps above. It uses `verus_syn` for accurate Verus syntax parsing.

**Verify it's working:**
```bash
uv run python -c "import verus_parser; print('✓ Rust parser available')"
```

**If the Rust build fails:** The tool falls back to regex-based extraction (less accurate but functional).

See [`rust-parser.md`](rust-parser.md) for details.

## Verify Installation

```bash
# Check CLI works
uv run python -m verus_lemma_finder --help

# Test search with included index
uv run python -m verus_lemma_finder search "division" data/vstd_lemma_index.json

# Start web demo
./demo/start_demo.sh
```

## First-Time Setup Notes

- **Model download:** The first search downloads the `all-MiniLM-L6-v2` model (~90 MB)
- **Embeddings:** Pre-built indexes in `data/` include embeddings, so semantic search works immediately

## Troubleshooting

### "ModuleNotFoundError: No module named 'verus_lemma_finder'"

```bash
# Ensure you're in the project directory
cd /path/to/verus_lemma_finder

# Re-sync dependencies
uv sync
```

### "Rust parser not available" warning

This is fine - the tool will use regex fallback. For best accuracy, build the Rust parser:

```bash
maturin develop --release
```

### "Command not found: verus-analyzer"

Only needed if building your own indexes. Install from:
https://github.com/verus-lang/verus-analyzer

### "Command not found: scip"

Only needed if building your own indexes. Download from:
https://github.com/sourcegraph/scip/releases

## Next Steps

- **Try the demo:** `./demo/start_demo.sh` → http://localhost:8000
- **Add your project:** `uv run python scripts/add_index.py`
- **Learn more:** [`usage.md`](usage.md)
