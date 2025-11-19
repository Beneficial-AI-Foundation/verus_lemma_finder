# Lemma Search Tool - Design & Implementation

## Overview

A semantic search tool for finding Verus lemmas and specs based on natural language queries, leveraging **verus-analyzer SCIP index** + lightweight spec extraction.

## Architecture

```
┌─────────────────────┐
│  verus-analyzer     │  Generates SCIP index
│  (SCIP export)      │  with symbols, docs, types
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  LemmaIndexer       │  Extracts:
│                     │  - Symbol metadata from SCIP
│                     │  - requires/ensures from source
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  lemma_index.json   │  Searchable index:
│                     │  - 304 lemmas/specs
│                     │  - Names, docs, signatures
│                     │  - Pre/postconditions
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  LemmaSearcher      │  Query strategies:
│                     │  - Keyword matching
│                     │  - Math normalization
│                     │  - (Future: embeddings)
└─────────────────────┘
```

## What We Get from SCIP

### ✅ Available Data

1. **Symbol IDs**: Unique identifiers for each function
   ```
   rust-analyzer cargo curve25519-dalek 4.1.3 div_mod_lemmas/common_lemmas/lemmas/lemma_mul_le_implies_div_le().
   ```

2. **Documentation**: Comments above functions (parsed as markdown)
   ```
   "Helper lemma: if a * b <= c and b > 0, then a <= c / b"
   ```

3. **Signatures**: Clean function signatures with types
   ```rust
   pub fn lemma_mul_le_implies_div_le(a: nat, b: nat, c: nat)
   ```

4. **File Locations**: Exact paths in codebase
   ```
   curve25519-dalek/src/lemmas/common_lemmas/div_mod_lemmas.rs
   ```

5. **Kind Information**: Function vs type vs module (kind=17 for functions)

6. **Call Graph Data**: References/occurrences for dependency analysis

### ❌ Not Directly Available (but extractable)

- `requires` clauses
- `ensures` clauses  
- `decreases` clauses
- Proof bodies

**Solution**: Simple regex-based extraction from source (works well enough for MVP)

## Current Implementation

### Phase 1: Indexing

```bash
uv run verus-lemma-finder index curve25519-dalek_scip.json -o lemma_index.json
```

**Process**:
1. Load SCIP JSON
2. Filter for function symbols (kind=17) in lemma/spec files
3. For each lemma:
   - Extract metadata from SCIP
   - Parse source file for `requires`/`ensures`
   - Store structured `LemmaInfo`

**Output**: JSON index with 304 lemmas

### Phase 2: Search

```bash
uv run verus-lemma-finder search "x <= z / y if x * y <= z" lemma_index.json
```

**Current Strategy** (keyword-based):
- Tokenize query and lemma metadata
- Score based on term overlap
- Boost matches in name (2x) and docs (1.5x)
- Math normalization (`div` → `/`, `leq` → `<=`, etc.)

**Output**: Ranked list with scores

### Phase 3: Interactive

```bash
uv run verus-lemma-finder interactive lemma_index.json
```

REPL for quick exploration.

## Example Results

### Query: "x <= z / y if x * y <= z and y > 0"

**Found**:
1. `lemma_mul_inequality` - general multiplication ordering
2. `lemma_div_is_ordered` - division preserves order
3. `lemma_div_strictly_bounded` - strict bounds on division

### Query: "if a times b <= c then a <= c div b"

**Found**:
1. `lemma_div_strictly_bounded` (exact match with documentation)
2. Related byte extraction lemmas
3. Other division lemmas

## Current Limitations

### 1. **Simple Keyword Search**
- No semantic understanding of mathematical equivalence
- `a * b <= c` vs `c >= b * a` treated as different
- `x / y` vs `x div y` require normalization

### 2. **Spec Parsing**
- Regex-based, doesn't handle complex nested expressions
- Might miss multi-line specs or complex formatting
- Comma-separated clauses sometimes incorrectly split

### 3. **No Context Awareness**
- Doesn't understand mathematical domains (nat vs int vs field)
- Can't reason about lemma relationships
- No dependency graph integration

### 4. **English-Only**
- Variable names matter (`a,b,c` vs `x,y,z`)
- Phrasing matters ("multiply" vs "product")

## Proposed Improvements

### Phase 2A: Better Parsing (Quick Win)

Use tree-sitter or verus LSP for proper AST-based extraction:
- Accurate `requires`/`ensures` parsing
- Handle nested expressions
- Extract bound variables correctly

### Phase 2B: Semantic Search (High Impact)

**Option 1: Lightweight Embeddings**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB model

# Pre-compute embeddings
lemma_embeddings = model.encode([l.to_searchable_text() for l in lemmas])

# At query time
query_embedding = model.encode(query)
similarities = cosine_similarity([query_embedding], lemma_embeddings)[0]
```

**Pros**:
- Fast (no LLM calls at query time)
- Offline after initial indexing
- Better semantic matching
- 80-400MB model size

**Cons**:
- May not understand mathematical equivalences perfectly
- Needs dependency (sentence-transformers)

**Option 2: LLM-Based RAG**

Use LLM for query understanding + ranking:
```python
# 1. Keyword search for top-50 candidates (fast filter)
candidates = keyword_search(query, k=50)

# 2. LLM re-ranks with mathematical reasoning
prompt = f"""
Query: {query}
Candidates:
{format_candidates(candidates)}

Rank these lemmas by relevance, considering mathematical equivalence.
"""
ranked = llm.rank(prompt)
```

**Pros**:
- Best understanding of mathematical equivalence
- Can explain why lemmas match
- Handles complex queries

**Cons**:
- Slower
- Requires API access or local LLM
- Cost per query

**Hybrid Approach** (Recommended):
1. Keyword search: top-50 (instant)
2. Embeddings: top-20 (fast)
3. LLM: top-5 with explanations (optional, on-demand)

### Phase 3: Mathematical Normalization

Build a normalization layer:
```python
def normalize_math_expr(expr: str) -> str:
    """Normalize mathematical expressions for matching"""
    # Commutative operations
    expr = sort_operands(expr, ops=['*', '+', 'and', 'or'])
    
    # Canonical forms
    expr = expr.replace('a * b', 'product(a, b)')
    expr = expr.replace('a / b', 'quotient(a, b)')
    
    # Standardize inequalities
    expr = flip_inequality_if_needed(expr)  # "c >= a*b" -> "a*b <= c"
    
    return expr
```

### Phase 4: Integration

**VS Code Extension**:
- Hover over function call → suggest relevant lemmas
- Command palette search
- Inline suggestions while writing `requires`/`ensures`

**CLI Integration**:
```bash
# Suggest lemmas for current proof context
verus-suggest --file scalar.rs --line 123

# Find similar lemmas
verus-similar lemma_mul_le_implies_div_le
```

**GitHub Bot**:
- PR reviews: "You might be duplicating lemma X"
- Issue suggestions: "Have you considered using lemma Y?"

### Phase 5: vstd Integration

Extend to index the entire Verus standard library:
```bash
# Index vstd
uv run verus-lemma-finder index --vstd /path/to/verus/source/vstd

# Search across project + vstd
uv run verus-lemma-finder search "array bounds check" --include-vstd
```

## Technical Decisions

### Why SCIP over custom parsing?

| Approach | Pros | Cons |
|----------|------|------|
| **Custom Parser** | Full control | Hard to maintain, breaks on syntax changes |
| **tree-sitter** | Accurate AST | Doesn't understand Verus semantics |
| **syn crate** | Rust native | Doesn't understand Verus extensions |
| **SCIP + verus-analyzer** ✅ | Already understands Verus, battle-tested, call graphs | Requires SCIP generation step |

SCIP wins because:
- **verus-analyzer already exists** and is maintained
- **Semantic understanding** of Verus-specific syntax
- **Call graph data** for free (useful for future features)
- **Incremental updates** possible
- **No reinventing the wheel**

### Why Python?

- Rapid prototyping
- Rich ML/NLP ecosystem (sentence-transformers, numpy, etc.)
- Easy JSON handling
- User-friendly CLI (could be Rust later for performance)

## Performance

**Current Stats**:
- SCIP file: 6.6 MB
- Index time: ~2 seconds
- Index file: ~150 KB (304 lemmas)
- Search time: <10ms per query
- Memory: ~20 MB

**With Embeddings**:
- Model size: 80-400 MB (one-time)
- Embedding time: +10 seconds during indexing
- Search time: ~50ms per query
- Memory: +50 MB

## Usage Examples

### Example 1: Find Division Lemma

```bash
$ uv run verus-lemma-finder search "if a * b <= c then a <= c / b" lemma_index.json -k 3

[1] lemma_mul_le_implies_div_le
    Helper lemma: if a * b <= c and b > 0, then a <= c / b
    requires: b > 0, a * b <= c
    ensures: a <= c / b
```

### Example 2: Interactive Exploration

```bash
$ uv run verus-lemma-finder interactive lemma_index.json

Search> modulo of power of 2

[1] lemma_mod_power_of_2 (score: 8.5)
[2] lemma_modular_bit_partitioning (score: 7.0)
[3] lemma_chunk_extraction_commutes_with_mod (score: 6.5)

Enter number for details: 1

📋 lemma_mod_power_of_2
   📂 curve25519-dalek/src/lemmas/common_lemmas/pow_lemmas.rs:234
   💬 Proof that taking the modulus of an integer by a power of 2...
   ...
```

### Example 3: Find Similar Lemmas

```python
# Future: find lemmas similar to one you're looking at
uv run verus-lemma-finder similar lemma_mul_le_implies_div_le lemma_index.json
```

## Next Steps

### Immediate (MVP working now ✅)
- [x] SCIP parsing
- [x] Basic indexing  
- [x] Keyword search
- [x] CLI interface
- [x] Interactive mode

### Short-term (1-2 days)
- [ ] Better spec parsing (handle multi-line, nested)
- [ ] Add embeddings for semantic search
- [ ] Math normalization (commutativity, canonical forms)
- [ ] Caching for faster repeated searches
- [ ] Add vstd lemmas to index

### Medium-term (1 week)
- [ ] VS Code extension
- [ ] Similar lemma finder (given a lemma, find related ones)
- [ ] Dependency graph integration (show which lemmas use others)
- [ ] Export to different formats (markdown, HTML)

### Long-term (Future)
- [ ] LLM-based re-ranking with explanations
- [ ] Auto-suggest during proof writing
- [ ] Proof pattern matching ("this looks like a proof of X")
- [ ] Integration with Verus tooling

## Comparison with Other Tools

| Tool | Approach | Pros | Cons |
|------|----------|------|------|
| **Coq's Search** | Pattern matching on types | Fast, precise | Requires exact pattern |
| **Isabelle Sledgehammer** | ATP integration | Finds proofs automatically | Heavy, not always explainable |
| **Lean's Mathlib search** | Embeddings + search | Semantic matching | Requires large corpus |
| **This tool** | SCIP + lightweight ML | Understands codebase, fast | Early stage, could be better |

## Conclusion

**Key Innovation**: Using `verus-analyzer` SCIP output as the foundation means we get:
- ✅ Accurate symbol information
- ✅ No parsing complexity
- ✅ Call graph data
- ✅ Incremental updates
- ✅ Battle-tested tooling

**Result**: A practical lemma search tool that **works today** and has a clear path to becoming much better with embeddings and LLM integration.

## Contributing

To improve the tool:

1. **Better scoring**: Tune the keyword matching weights
2. **Math equivalence**: Add more normalization rules
3. **Add embeddings**: Integrate sentence-transformers
4. **Parser improvements**: Use tree-sitter for spec extraction
5. **UI/UX**: Build VS Code extension or web interface

## References

- [SCIP Protocol](https://github.com/sourcegraph/scip)
- [verus-analyzer](https://github.com/verus-lang/verus-analyzer)
- [sentence-transformers](https://www.sbert.net/)
- [Semantic Code Search (GitHub)](https://github.blog/2023-02-06-semantic-code-search/)

