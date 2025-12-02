# vstd Integration Guide

## Overview

The lemma search tool can index lemmas from **vstd** (Verus standard library) alongside your project's lemmas. This helps you discover existing standard library lemmas before writing your own!

## Quick Start

### Option 1: Use the add_index script (Recommended)

```bash
uv run python scripts/add_index.py --name vstd \
    --path /path/to/verus/source/vstd \
    --scip /path/to/vstd_index_scip.json \
    --github-url https://github.com/verus-lang/verus \
    --github-path-prefix source/vstd/
```

### Option 2: Manual CLI commands

#### 1. Setup vstd (one-time)

```bash
# Clone the Verus repository
uv run python -m verus_lemma_finder setup-vstd ./verus

# Or clone manually
git clone --depth 1 https://github.com/verus-lang/verus.git ./verus
```

#### 2. Generate SCIP for vstd

```bash
cd ./verus/source
verus-analyzer scip .
scip print --json index.scip > vstd_index_scip.json
```

**Note**: This step may take a few minutes.

#### 3. Build the vstd Index

```bash
uv run python -m verus_lemma_finder index \
    ./verus/source/vstd_index_scip.json \
    -o data/vstd_lemma_index.json \
    --source-root ./verus/source
```

#### 4. Add vstd Lemmas to an Existing Index

```bash
uv run python -m verus_lemma_finder add-vstd \
    ./verus/source/vstd_index_scip.json \
    data/project_lemma_index.json \
    -o data/combined_lemma_index.json
```

## Search Results with vstd

When you search, results show the source:

```
📋 lemma_div_mul_cancel (vstd)
   📦 arithmetic/div_mod.rs:42
   💬 Proves that (a * b) / b == a when b > 0
   ✍️  pub proof fn lemma_div_mul_cancel(a: int, b: int)
   ✓ requires:
      • b > 0
   ✓ ensures:
      • (a * b) / b == a

📋 lemma_mul_le_implies_div_le (project)
   📁 src/lemmas/div_mod.rs:23
   💬 Your project lemma
   ...
```

Notice:
- **📦** icon and **(vstd)** label for standard library lemmas
- **📁** icon for your project lemmas

## Architecture

### Data Model

Each lemma has a `source` field:

```python
@dataclass
class LemmaInfo:
    name: str
    file_path: str
    # ... other fields ...
    source: str = "project"  # "project", "vstd", or custom
```

### Path Filtering

When indexing vstd, the tool:
1. Loads the SCIP JSON
2. Indexes all proof functions
3. Tags them with `source: "vstd"`

### Index Merging

The merge process:
1. Loads your existing index (project lemmas)
2. Loads vstd lemmas
3. Combines lemma lists
4. Merges embeddings (if available for both)
5. Saves combined index

## Advanced Usage

### Filtering by Source in Code

```python
from verus_lemma_finder import LemmaSearcher

searcher = LemmaSearcher('data/combined_lemma_index.json')
results = searcher.fuzzy_search("division properties")

# Filter to only vstd
vstd_results = [(lemma, score) for lemma, score in results 
                if lemma.source == "vstd"]

# Filter to only project
project_results = [(lemma, score) for lemma, score in results 
                   if lemma.source == "project"]
```

### Updating vstd Lemmas

To update vstd lemmas (e.g., after a Verus update):

```bash
# 1. Update the Verus repository
cd ./verus
git pull
cd ..

# 2. Regenerate SCIP
cd ./verus/source
verus-analyzer scip .
scip print --json index.scip > vstd_index_scip.json
cd ../..

# 3. Rebuild the vstd index
uv run python -m verus_lemma_finder index \
    ./verus/source/vstd_index_scip.json \
    -o data/vstd_lemma_index.json \
    --source-root ./verus/source
```

## Performance Considerations

### SCIP Generation Time

- **Small project**: ~10-30 seconds
- **Verus repository**: ~2-5 minutes

### Index Size

Example sizes with embeddings:

| Index Content | Lemmas | JSON Size | Embeddings Size |
|---------------|--------|-----------|-----------------|
| Project only | ~150 | 0.5 MB | 0.5 MB |
| vstd only | ~400-500 | 1-2 MB | 1-2 MB |
| Combined | ~550-650 | 1.5-2.5 MB | 1.5-2.5 MB |

### Search Performance

Search performance is largely unaffected:
- Semantic search scales linearly with number of lemmas (very fast even for 1000s)
- Memory usage: ~5-10 MB for combined index

## Troubleshooting

### "No vstd lemmas found"

**Problem**: After indexing, you see "0 lemmas indexed".

**Possible causes**:
1. SCIP was generated from wrong directory
2. The SCIP file is corrupted or empty

**Solution**:
```bash
# Check the SCIP file is valid JSON
python -c "import json; json.load(open('vstd_index_scip.json'))"

# Check it has documents
python -c "import json; d=json.load(open('vstd_index_scip.json')); print(len(d.get('documents', [])))"
```

### Embeddings Warning

**Problem**: "Warning: sentence-transformers not available"

**Solution**:
```bash
uv sync --extra dev
```

## Command Reference

### `setup-vstd`

Clone the Verus repository to access vstd.

```bash
uv run python -m verus_lemma_finder setup-vstd [TARGET_DIR]

# Parameters:
#   TARGET_DIR: Where to clone Verus (default: ./verus)
```

### `add-vstd`

Add vstd lemmas to an existing index.

```bash
uv run python -m verus_lemma_finder add-vstd VERUS_SCIP BASE_INDEX [OPTIONS]

# Parameters:
#   VERUS_SCIP: Path to Verus SCIP JSON file
#   BASE_INDEX: Path to your existing lemma index
#
# Options:
#   -o, --output FILE      Output file (default: overwrites BASE_INDEX)
#   -r, --verus-root DIR   Verus repo root (default: SCIP file directory)
```

### `index`

Build a searchable index from SCIP data.

```bash
uv run python -m verus_lemma_finder index SCIP_FILE [OPTIONS]

# Options:
#   -o, --output FILE      Output index file
#   --source-root PATH     Root path for source files
#   --no-embeddings        Skip embedding generation
```

## FAQ

### Q: Do I need to add vstd to search it?

**A**: Yes. vstd lemmas are not included by default because:
1. Indexing takes extra time
2. Larger index size
3. You might not always need standard library lemmas

### Q: Will adding vstd slow down searches?

**A**: Not noticeably. Semantic search is very fast even with 1000+ lemmas.

### Q: How often should I update vstd?

**A**: When you update your Verus installation or when new stdlib lemmas might be relevant.

### Q: Can I search only vstd or only project lemmas?

**A**: Not directly in the CLI yet, but you can filter programmatically (see "Advanced Usage" above).

## Summary

The vstd integration enables you to:
- ✅ Search standard library lemmas alongside your project
- ✅ Avoid rewriting lemmas that exist in vstd
- ✅ Learn from standard library patterns
- ✅ See source annotations in search results
- ✅ Maintain separation between project and stdlib code
