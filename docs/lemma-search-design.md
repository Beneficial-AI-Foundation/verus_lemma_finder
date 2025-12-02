# Lemma Search Tool - Design & Architecture

## Overview

A semantic search tool for finding Verus lemmas and specs based on natural language queries. Uses a **hybrid Rust + Python architecture**:
- **Rust + verus_syn**: Accurate parsing of Verus syntax
- **Python + sentence-transformers**: Semantic embeddings and search

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Verus Lemma Finder                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │  verus-analyzer │         │  🦀 Rust (verus_syn)    │   │
│  │  (SCIP export)  │────────>│  • AST-based parsing    │   │
│  └─────────────────┘         │  • Spec extraction      │   │
│          │                   │  • PyO3 bindings        │   │
│          v                   └───────────┬─────────────┘   │
│  ┌─────────────────┐                     │                 │
│  │  SCIP JSON      │                     v                 │
│  │  (symbols,docs) │         ┌─────────────────────────┐   │
│  └────────┬────────┘         │  🐍 Python              │   │
│           │                  │  • sentence-transformers│   │
│           v                  │  • Semantic search      │   │
│  ┌─────────────────┐         │  • Query normalization  │   │
│  │  LemmaIndexer   │────────>│  • CLI & Web interface  │   │
│  │  (Python)       │         └─────────────────────────┘   │
│  └────────┬────────┘                                       │
│           │                                                 │
│           v                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  lemma_index.json + embeddings.npy                  │   │
│  │  • Lemma metadata (name, docs, signature)           │   │
│  │  • requires/ensures/decreases clauses               │   │
│  │  • Pre-computed semantic embeddings                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. SCIP Generation (verus-analyzer)

```bash
cd /path/to/verus/project
verus-analyzer scip .
scip print --json index.scip > project_scip.json
```

**Output**: JSON with symbols, documentation, signatures, file locations

### 2. Indexing (Python + Rust)

```bash
uv run python -m verus_lemma_finder index project_scip.json -o lemma_index.json
```

**Process**:
1. Load SCIP JSON
2. Filter for function symbols (kind=17) matching lemma patterns
3. For each lemma:
   - Extract metadata from SCIP (name, docs, signature)
   - Use Rust parser (verus_syn) to extract `requires`/`ensures`/`decreases`
   - Compute semantic embedding
4. Save index + embeddings

### 3. Search (Python)

```bash
uv run python -m verus_lemma_finder search "division properties" lemma_index.json
```

**Process**:
1. Normalize query (operators, variables, implications)
2. Generate query variations
3. Compute query embedding
4. Cosine similarity against lemma embeddings
5. Return ranked results

## Components

### Rust Parser (`rust/src/lib.rs`)

Uses `verus_syn` for accurate Verus syntax parsing:

```rust
// Extract specs from a function
fn extract_function_specs(content: &str, function_name: &str) -> FunctionSpecs {
    // Parse with verus_syn
    let file = verus_syn::parse_file(content)?;
    
    // Visit AST to find function and extract specs
    let mut finder = FunctionFinder::new(function_name);
    finder.visit_file(&file);
    
    finder.specs  // { requires: [...], ensures: [...], decreases: [...] }
}
```

**Handles**:
- Top-level functions
- Methods in `impl` blocks
- Trait methods
- Functions inside `verus!` macros
- Nested modules

### Python Indexer (`src/verus_lemma_finder/indexing.py`)

```python
class LemmaIndexer:
    def build_index(self) -> LemmaIndex:
        for doc in scip_data["documents"]:
            for symbol in doc["symbols"]:
                if self._should_index_symbol(symbol):
                    lemma = self._extract_lemma_info(symbol, doc)
                    lemmas.append(lemma)
        
        if self.use_embeddings:
            embeddings = self._compute_embeddings(lemmas)
        
        return LemmaIndex(lemmas, embeddings)
```

### Python Searcher (`src/verus_lemma_finder/search.py`)

```python
class LemmaSearcher:
    def fuzzy_search(self, query: str, top_k: int = 10):
        # Normalize and generate variations
        variations = self._generate_query_variations(query)
        
        # Compute embeddings for all variations
        query_embeddings = model.encode(variations)
        
        # Find best matches
        similarities = cosine_similarity(query_embeddings, self.embeddings)
        
        return self._rank_results(similarities, top_k)
```

### Query Normalization (`src/verus_lemma_finder/normalization.py`)

```python
def normalize_query(query: str) -> str:
    # Operator normalization: "times" → "*", "div" → "/"
    query = normalize_operators(query)
    
    # Variable normalization: "a,b,c" → "var1,var2,var3"
    query = normalize_variables(query)
    
    return query

def generate_variations(query: str) -> List[str]:
    # Generate equivalent phrasings
    # "if A then B" ↔ "B if A"
    return variations
```

## Data Models

### LemmaInfo

```python
@dataclass
class LemmaInfo:
    name: str                    # lemma_mul_le_implies_div_le
    file_path: str               # src/lemmas/div_mod.rs
    line_number: Optional[int]   # 42
    documentation: str           # "Proves that..."
    signature: str               # pub proof fn lemma_...(a: int, b: int)
    requires_clauses: List[str]  # ["b > 0", "a * b <= c"]
    ensures_clauses: List[str]   # ["a <= c / b"]
    decreases_clauses: List[str] # []
    source: str                  # "project" or "vstd"
```

### Index Format

```json
{
  "lemmas": [...],
  "version": "1.0",
  "source": "project",
  "created_at": "2024-01-01T00:00:00Z"
}
```

Embeddings stored separately as `.npy` file for efficiency.

## Search Strategies

### 1. Semantic Search (Default)

Uses sentence-transformers (`all-MiniLM-L6-v2`) for semantic similarity:
- Understands synonyms ("divide" ≈ "division")
- Handles paraphrasing
- Fast (~50ms per query)

### 2. Keyword Search (Fallback)

Token-based matching when embeddings unavailable:
- Exact term matching
- Boost for name matches (2x)
- Boost for documentation matches (1.5x)

### 3. Hybrid Search

Combines both for best results:
- Semantic score (70%)
- Keyword score (30%)

## Performance

| Metric | Value |
|--------|-------|
| Index build time | ~10-30 seconds |
| Search latency | <100ms |
| Model size | ~90 MB |
| Index size (400 lemmas) | ~2 MB |
| Embeddings size | ~600 KB |
| Memory usage | ~100 MB |

## Why This Architecture?

### Why Rust for Parsing?

| Approach | Pros | Cons |
|----------|------|------|
| Regex (Python) | Simple | Breaks on complex syntax |
| tree-sitter | Accurate AST | Doesn't understand Verus |
| syn (Rust) | Rust native | No Verus extensions |
| **verus_syn** ✅ | Proper Verus AST | Requires Rust build |

**verus_syn wins** because it understands Verus-specific syntax like `requires`, `ensures`, `proof fn`, etc.

### Why Python for Search?

- Rich ML ecosystem (sentence-transformers, numpy)
- Fast prototyping
- Easy JSON handling
- User-friendly CLI

### Why PyO3 Bridge?

- Best of both worlds
- Single package distribution
- No subprocess overhead

## Comparison with Other Approaches

| Tool | Approach | Pros | Cons |
|------|----------|------|------|
| Grep/ripgrep | Text search | Fast, simple | No semantic understanding |
| verus-find | AST patterns | Exact matching | Can't find by meaning |
| **This tool** | Semantic + AST | Natural language queries | Requires embeddings |

## Future Directions

### Potential Enhancements

1. **Source filtering**: `--source=vstd` flag for CLI
2. **Similar lemma finder**: Given a lemma, find related ones
3. **VS Code extension**: Inline suggestions
4. **LLM re-ranking**: Use LLM for complex queries

### Not Planned

- Full proof synthesis (out of scope)
- Real-time indexing (batch is sufficient)

## References

- [SCIP Protocol](https://github.com/sourcegraph/scip)
- [verus-analyzer](https://github.com/verus-lang/verus-analyzer)
- [verus_syn](https://crates.io/crates/verus_syn)
- [sentence-transformers](https://www.sbert.net/)
- [PyO3](https://pyo3.rs/)
