# Python API

Simple functions for integrating lemma search into your code.

## Quick Start

```python
from verus_lemma_finder import get_similar_lemmas, get_similar_to_lemma, load_searcher

# Search by natural language query
results = get_similar_lemmas(
    query="modulo is less than divisor",
    index_path="data/vstd_lemma_index.json",
    top_k=3
)

# Find lemmas similar to an existing lemma
results = get_similar_to_lemma(
    lemma_name="lemma_mod_adds",
    index_path="data/vstd_lemma_index.json",
    top_k=3
)

for r in results:
    print(f"{r.name}: {r.score:.2f}")
    print(f"  {r.file_path}:{r.line_number}")
```

## Functions

### `get_similar_lemmas`

Find lemmas matching a query. Auto-detects if the query is a lemma name.

```python
def get_similar_lemmas(
    query: str,
    index_path: str | Path | None = None,
    searcher: LemmaSearcher | None = None,
    top_k: int = 3,
    exclude_self: bool = True,
    auto_detect_lemma: bool = True,
) -> list[SimilarLemma]
```

**Parameters:**
- `query` - Natural language query or lemma name
- `index_path` - Path to index file (required if `searcher` not provided)
- `searcher` - Pre-loaded searcher (for multiple queries)
- `top_k` - Number of results
- `exclude_self` - Exclude exact name matches
- `auto_detect_lemma` - If query matches a lemma name, use its definition

**Returns:** List of `SimilarLemma` objects.

### `get_similar_to_lemma`

Find lemmas similar to an existing lemma by name.

```python
def get_similar_to_lemma(
    lemma_name: str,
    index_path: str | Path | None = None,
    searcher: LemmaSearcher | None = None,
    top_k: int = 3,
) -> list[SimilarLemma]
```

**Parameters:**
- `lemma_name` - Exact name of lemma in the index
- `index_path` - Path to index file
- `searcher` - Pre-loaded searcher
- `top_k` - Number of results

**Returns:** List of `SimilarLemma` objects. Empty list if lemma not found.

### `load_searcher`

Load a searcher for multiple queries (more efficient).

```python
def load_searcher(
    index_path: str | Path,
    use_embeddings: bool = True
) -> LemmaSearcher
```

## Data Types

### `SimilarLemma`

```python
@dataclass
class SimilarLemma:
    name: str           # Lemma name
    score: float        # Similarity score (higher = more similar)
    file_path: str      # Source file
    line_number: int    # Line number (may be None)
    signature: str      # Function signature
    source: str         # "project" or "vstd"
    
    def to_dict(self) -> dict  # For JSON serialization
```

## Usage Patterns

### Single Query

```python
from verus_lemma_finder import get_similar_lemmas

results = get_similar_lemmas(
    "remainder bounds",
    index_path="data/vstd_lemma_index.json"
)
```

### Multiple Queries (Efficient)

Load the searcher once and reuse:

```python
from verus_lemma_finder import load_searcher, get_similar_lemmas

searcher = load_searcher("data/vstd_lemma_index.json")

for query in queries:
    results = get_similar_lemmas(query, searcher=searcher)
```

### Lemma-to-Lemma Similarity

Find lemmas similar to a known lemma:

```python
from verus_lemma_finder import get_similar_to_lemma

# Option 1: Explicit function
results = get_similar_to_lemma("lemma_mod_adds", index_path="data/vstd_lemma_index.json")

# Option 2: Auto-detected (same result)
results = get_similar_lemmas("lemma_mod_adds", index_path="data/vstd_lemma_index.json")
```

### JSON Output

Use the `_dict` variants for JSON serialization:

```python
from verus_lemma_finder import get_similar_lemmas_dict, get_similar_to_lemma_dict
import json

results = get_similar_lemmas_dict("modulo bounds", index_path="data/vstd_lemma_index.json")
print(json.dumps(results, indent=2))
```

## Advanced: Direct Searcher Access

For full control, use `LemmaSearcher` directly:

```python
from verus_lemma_finder import LemmaSearcher
from pathlib import Path

searcher = LemmaSearcher(Path("data/vstd_lemma_index.json"))

# Various search methods
results = searcher.search("query", top_k=10)           # Default (fuzzy)
results = searcher.semantic_search("query", top_k=10)  # Embeddings only
results = searcher.keyword_search("query", top_k=10)   # Keywords only
results = searcher.hybrid_search("query", top_k=10)    # Combined

# Lemma lookup
lemma = searcher.get_lemma_by_name("lemma_mod_adds")
results = searcher.find_similar_lemmas("lemma_mod_adds", top_k=5)
```

