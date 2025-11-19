# vstd Integration Guide

## Overview

The lemma search tool can now index lemmas from **vstd** (Verus standard library) alongside your project's lemmas. This helps you discover existing standard library lemmas before writing your own!

## Quick Start

### 1. Setup vstd (one-time)

```bash
# Clone the Verus repository
uv run verus-lemma-finder setup-vstd ./verus

# Or specify a different location
uv run verus-lemma-finder setup-vstd /path/to/verus
```

This will clone the Verus repository (shallow clone for speed).

### 2. Generate SCIP for Verus

```bash
# Generate SCIP JSON for the entire Verus repository
uv run verus-lemma-finder generate-scip ./verus

# Or manually
cd ./verus
verus-analyzer scip .
scip print --json index.scip > verus_scip.json
```

**Note**: This step may take a few minutes as Verus is a large codebase.

### 3. Add vstd Lemmas to Your Index

```bash
# Merge vstd lemmas into your existing index
uv run verus-lemma-finder add-vstd ./verus/verus_scip.json lemma_index.json

# Or use Python directly
uv run verus-lemma-finder add-vstd \
    ./verus/verus_scip.json \
    lemma_index.json \
    -o lemma_index_with_vstd.json
```

**Important**: This command:
- Only indexes files under `source/vstd/` (filters out other Verus code)
- Preserves your existing project lemmas
- Tags vstd lemmas with `source: "vstd"`
- Merges embeddings if both indexes have them

## Complete Workflow Example

```bash
# 1. Setup your project index (if not done already)
uv run verus-lemma-finder reindex

# 2. Setup vstd
uv run verus-lemma-finder setup-vstd ./verus

# 3. Generate SCIP for Verus
uv run verus-lemma-finder generate-scip ./verus

# 4. Add vstd lemmas
uv run verus-lemma-finder add-vstd ./verus/verus_scip.json lemma_index.json

# 5. Search across both!
uv run verus-lemma-finder search "division properties"
uv run verus-lemma-finder interactive
```

## Search Results with vstd

When you search, results will show the source:

```
📋 lemma_div_mul_cancel (vstd)
   📦 source/vstd/arithmetic/div_mod.rs:42
   💬 Proves that (a * b) / b == a when b > 0
   ✍️  pub proof fn lemma_div_mul_cancel(a: int, b: int)
   ✓ requires:
      • b > 0
   ✓ ensures:
      • (a * b) / b == a

📋 lemma_mul_le_implies_div_le
   📁 curve25519-dalek/src/lemmas/common_lemmas/div_mod_lemmas.rs:23
   💬 Your project lemma
   ...
```

Notice:
- **📦** icon and **(vstd)** label for standard library lemmas
- **📁** icon for your project lemmas
- Full paths so you know where each lemma comes from

## Architecture

### Data Model

Each lemma now has a `source` field:

```python
@dataclass
class LemmaInfo:
    name: str
    file_path: str
    # ... other fields ...
    source: str = "project"  # "project", "vstd", or other
```

### Path Filtering

When indexing vstd, the tool:
1. Loads the entire Verus SCIP JSON
2. Filters to only files starting with `source/vstd/`
3. Indexes only those lemmas
4. Tags them with `source: "vstd"`

### Index Merging

The merge process:
1. Loads your existing index (project lemmas)
2. Indexes vstd lemmas separately
3. Combines lemma lists
4. Merges embeddings (if available for both)
5. Saves combined index

## Advanced Usage

### Multiple Sources

You can add multiple sources to your index:

```bash
# Add vstd
uv run verus-lemma-finder add-vstd \
    ./verus/verus_scip.json \
    lemma_index.json

# Add another library (hypothetically)
# You'd need to modify source parameter for custom sources
```

### Filtering by Source in Searches

Currently, all sources are searched together. To filter by source, you can:

```python
# In Python REPL or script
from lemma_search_tool import LemmaSearcher

searcher = LemmaSearcher('lemma_index.json')
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
uv run verus-lemma-finder generate-scip ./verus

# 3. Rebuild your entire index
uv run verus-lemma-finder reindex  # Rebuild project index

# 4. Re-add vstd
uv run verus-lemma-finder add-vstd ./verus/verus_scip.json lemma_index.json
```

## Performance Considerations

### SCIP Generation Time

- **curve25519-dalek**: ~10-30 seconds
- **Verus repository**: ~2-5 minutes (it's much larger)

### Index Size

Example sizes with embeddings:

| Index Content | Lemmas | JSON Size | Embeddings Size |
|--------------|--------|-----------|----------------|
| Project only | ~150 | 0.5 MB | 0.5 MB |
| vstd only | ~500-1000 | 2-4 MB | 2-4 MB |
| Combined | ~650-1150 | 2.5-4.5 MB | 2.5-4.5 MB |

*(Actual numbers depend on how many lemmas are in each)*

### Search Performance

Search performance is largely unaffected:
- Semantic search: Scales linearly with number of lemmas (very fast even for 1000s)
- Memory usage: ~5-10 MB for combined index

## Troubleshooting

### "No vstd lemmas found"

**Problem**: After running `add-vstd`, you see "No vstd lemmas found".

**Possible causes**:
1. SCIP was generated from wrong directory
2. vstd lemmas might not have standard naming (lemma_, axiom_, etc.)

**Solution**:
```bash
# Check the SCIP file
grep -i "vstd" verus_scip.json | head -20

# If paths don't start with "source/vstd/", adjust path_filter
```

### Git Clone Fails

**Problem**: `setup-vstd` fails to clone.

**Solution**:
```bash
# Clone manually
git clone --depth 1 https://github.com/verus-lang/verus.git ./verus

# Then continue with generate-scip
uv run verus-lemma-finder generate-scip ./verus
```

### Embeddings Mismatch

**Problem**: "Warning: Base index has embeddings but sentence-transformers not available"

**Solution**:
```bash
# Install dependencies
uv sync
```

### Index Overwritten Accidentally

**Problem**: You ran `add-vstd` and it overwrote your index.

**Solution**: By default, `add-vstd` overwrites the base index. To keep both:
```bash
# Specify different output
uv run verus-lemma-finder add-vstd \
    ./verus/verus_scip.json \
    lemma_index.json \
    -o lemma_index_with_vstd.json
```

## Command Reference

### `setup-vstd`

Clone the Verus repository to access vstd.

```bash
uv run verus-lemma-finder setup-vstd [TARGET_DIR]

# Parameters:
#   TARGET_DIR: Where to clone Verus (default: ./verus)
```

**Options**:
- Uses shallow clone (`--depth 1`) for speed
- Interactive: asks if directory already exists

### `add-vstd`

Add vstd lemmas to an existing index.

```bash
uv run verus-lemma-finder add-vstd VERUS_SCIP BASE_INDEX [OPTIONS]

# Parameters:
#   VERUS_SCIP: Path to Verus SCIP JSON file
#   BASE_INDEX: Path to your existing lemma index
#
# Options:
#   -o, --output FILE      Output file (default: overwrites BASE_INDEX)
#   -r, --verus-root DIR   Verus repo root (default: SCIP file directory)
```

**Behavior**:
- Automatically detects if base index has embeddings
- Computes embeddings for vstd if base has them
- Filters to only `source/vstd/` files
- Tags lemmas with `source: "vstd"`

## FAQ

### Q: Do I need to add vstd to search it?

**A**: Yes. vstd lemmas are not included by default because:
1. Indexing takes extra time
2. Larger index size
3. You might not always need standard library lemmas

### Q: Can I add other libraries?

**A**: The current implementation is optimized for vstd, but you could adapt it:

```python
# Create custom indexer with different source and path filter
indexer = LemmaIndexer(
    other_lib_scip, 
    other_lib_root,
    use_embeddings=True,
    source="my_library",
    path_filter="path/to/library/lemmas"
)
```

### Q: Will adding vstd slow down searches?

**A**: Not noticeably. Semantic search is very fast even with 1000+ lemmas.

### Q: How often should I update vstd?

**A**: When you update your Verus installation or when new stdlib lemmas might be relevant to your work.

### Q: Can I search only vstd or only project lemmas?

**A**: Not directly in the CLI yet, but you can filter programmatically (see "Advanced Usage" above). A future enhancement could add a `--source` filter flag.

## Future Enhancements

Potential improvements:
1. **Source filtering**: `uv run verus-lemma-finder search --source=vstd "query"`
2. **Auto-update**: Periodic vstd sync
3. **Other libraries**: Support for third-party Verus libraries
4. **Preference ranking**: Prefer project lemmas over vstd in results
5. **Namespace awareness**: Show module/namespace in results

## Summary

The vstd integration enables you to:
- ✅ Search standard library lemmas alongside your project
- ✅ Avoid rewriting lemmas that exist in vstd
- ✅ Learn from standard library patterns
- ✅ See source annotations in search results
- ✅ Maintain separation between project and stdlib code


