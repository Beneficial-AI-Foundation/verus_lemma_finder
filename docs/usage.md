# Usage Guide

Detailed guide for using verus_lemma_finder.

## Quick Reference

| Task | Command |
|------|---------|
| Add new project index | `uv run python scripts/add_index.py` |
| Search lemmas | `uv run python -m verus_lemma_finder search "query" index.json` |
| Interactive mode | `uv run python -m verus_lemma_finder interactive index.json` |
| Start web demo | `./demo/start_demo.sh` |

## Adding a New Index

### Method 1: Interactive Script (Recommended)

The easiest way to add a new index:

```bash
uv run python scripts/add_index.py
```

This walks you through:
1. Project name and path
2. SCIP generation (or use existing SCIP file)
3. Embedding generation
4. Demo server integration

### Method 2: Non-Interactive Script

For scripting/automation:

```bash
# Minimal (uses defaults)
uv run python scripts/add_index.py --name myproject --path /path/to/project

# With GitHub integration
uv run python scripts/add_index.py --name myproject --path /path/to/project \
    --github-url https://github.com/user/repo

# Using existing SCIP file
uv run python scripts/add_index.py --name myproject --path /path/to/project \
    --scip /path/to/existing_scip.json

# With path prefix for GitHub URLs
uv run python scripts/add_index.py --name myproject --path /path/to/project \
    --github-url https://github.com/user/repo \
    --github-path-prefix src/

# Skip demo server setup
uv run python scripts/add_index.py --name myproject --path /path/to/project --no-demo

# Skip embedding generation
uv run python scripts/add_index.py --name myproject --path /path/to/project --no-embeddings
```

### Method 3: Manual CLI Commands

For fine-grained control:

```bash
# Step 1: Generate SCIP (in your project directory)
cd /path/to/your/project
verus-analyzer scip .
scip print --json index.scip > project_scip.json

# Step 2: Build the searchable index
uv run python -m verus_lemma_finder index project_scip.json \
    -o data/myproject_lemma_index.json

# Step 3: (Optional) Manually add to demo/server.py GITHUB_REPOS config
```

## Searching

### Command Line Search

```bash
# Basic search
uv run python -m verus_lemma_finder search "division properties" lemma_index.json

# More results
uv run python -m verus_lemma_finder search "query" lemma_index.json -k 10

# Keyword-only search (no embeddings)
uv run python -m verus_lemma_finder search "query" lemma_index.json --keyword-only

# Hybrid search (embeddings + keywords)
uv run python -m verus_lemma_finder search "query" lemma_index.json --hybrid
```

### Interactive Mode

```bash
uv run python -m verus_lemma_finder interactive lemma_index.json
```

This starts a REPL where you can:
- Type queries and see results instantly
- Refine searches
- Exit with `quit` or `Ctrl+C`

### Web Interface

```bash
./demo/start_demo.sh
```

Then open http://localhost:8000 in your browser.

## vstd Integration

vstd is the Verus standard library. You can index it for searching.

### Quick Method

```bash
uv run python scripts/add_index.py --name vstd \
    --path /path/to/verus/source/vstd \
    --scip /path/to/vstd_index_scip.json \
    --github-url https://github.com/verus-lang/verus \
    --github-path-prefix source/vstd/
```

### Manual Method

```bash
# Clone Verus repository
git clone https://github.com/verus-lang/verus.git
cd verus/source

# Generate SCIP
verus-analyzer scip .
scip print --json index.scip > vstd_index_scip.json

# Build the index
cd /path/to/verus_lemma_finder
uv run python -m verus_lemma_finder index /path/to/vstd_index_scip.json \
    -o data/vstd_lemma_index.json \
    --source-root /path/to/verus/source

# Or use the built-in commands
uv run python -m verus_lemma_finder setup-vstd ./verus
uv run python -m verus_lemma_finder add-vstd ./verus/verus_scip.json existing_index.json
```

## CLI Command Reference

### `index` - Build a searchable index

```bash
uv run python -m verus_lemma_finder index <scip_file> [options]

Options:
  -o, --output FILE      Output index file (default: lemma_index.json)
  --no-embeddings        Skip embeddings (keyword search only; embeddings enabled by default)
  --source-root PATH     Root path for source files
  --path-filter PREFIX   Only index files starting with this prefix
```

### `search` - Search lemmas

```bash
uv run python -m verus_lemma_finder search <query> <index_file> [options]

Options:
  -k, --top-k N          Number of results (default: 5)
  --keyword-only         Use keyword search only (no embeddings)
  --hybrid               Use hybrid search (embeddings + keywords)
```

### `interactive` - Interactive search REPL

```bash
uv run python -m verus_lemma_finder interactive <index_file>
```

### `setup-vstd` - Clone and prepare Verus repo

```bash
uv run python -m verus_lemma_finder setup-vstd <destination>
```

### `add-vstd` - Add vstd lemmas to an existing index

```bash
uv run python -m verus_lemma_finder add-vstd <scip_file> <existing_index> [options]

Options:
  -o, --output FILE      Output combined index file
  --verus-root PATH      Path to Verus repository root
```

### `generate-scip` - Generate SCIP from a Verus project

```bash
uv run python -m verus_lemma_finder generate-scip <project_path> [options]

Options:
  -o, --output FILE      Output SCIP JSON file
```

## Query Tips

### Natural Language Works

```bash
# All of these find the same lemmas:
"division distributes over addition"
"a / b + a / c"  
"how to split a division"
```

### Query Normalization

Variable names and math notation are normalized, so these are equivalent:

```bash
"if a * b <= c then a <= c / b"
"x <= z / y when x * y <= z"
"m <= p / n if m * n <= p"
```

### Operators

Common operators are recognized:

| You can write | Also matches |
|---------------|--------------|
| `*`, `times` | multiplication |
| `/`, `div` | division |
| `<=`, `le`, `less than or equal` | comparison |
| `==>`, `implies` | implication |
| `forall`, `for all` | universal quantifier |
| `exists` | existential quantifier |

## Troubleshooting

### "No results found"

1. Check the index file exists and has embeddings
2. Try broader queries
3. Use `--keyword-only` to see if keyword search finds anything

### "Rust parser not available"

Build the Rust parser for better accuracy:

```bash
cd rust && maturin develop --release
```

### SCIP generation fails

1. Ensure `verus-analyzer` is installed and in PATH
2. Ensure `scip` CLI is installed
3. Check that the project compiles with Verus

## See Also

- [Installation Guide](install.md)
- [Search Tips](search-tips.md)
- [Rust Parser Details](rust-parser.md)
- [Comparison with verus-find](comparison-with-verus-find.md)
- [vstd Integration Guide](vstd-integration-guide.md)

