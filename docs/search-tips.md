# Lemma Search Tips

## Getting the Best Results

### 1. The tool now normalizes your queries automatically!

You can write queries in any of these equivalent forms:

**All of these will produce similar results:**
```
"if a times b <= c then a <= c div b"
"if x * y <= z then x <= z / y"
"x <= z / y if x * y <= z"
"a <= c div b when a mul b <= c"
```

The tool will:
- Convert word forms (`times`, `div`) to operators (`*`, `/`)
- Normalize variable names (`a,b,c` → `var1,var2,var3`)
- Generate multiple phrasings (if-then and then-if)
- Search with all variations

### 2. Write queries in natural mathematical language

✅ **Good query examples:**
```
"if a * b <= c and b > 0 then a <= c / b"
"x + y = z implies x = z - y"
"multiplication is commutative"
"modular arithmetic reduction"
"if n is even then n mod 2 equals 0"
```

❌ **Less effective:**
```
"lemma_mul_le"  (too specific to implementation names)
"division"      (too vague)
```

### 3. Use mathematical notation you're comfortable with

The tool understands multiple notations:

| You can write | Will be normalized to |
|---------------|----------------------|
| `times`, `mul`, `multiply` | `*` |
| `div`, `divide` | `/` |
| `mod`, `modulo` | `%` |
| `leq` | `<=` |
| `geq` | `>=` |
| `neq` | `!=` |
| `iff` | `if and only if` |

### 4. Don't worry about variable names

These are all equivalent:
- `"if a * b = c then ..."`
- `"if x * y = z then ..."`
- `"if m * n = p then ..."`

The tool normalizes them to the same generic form.

### 5. State implications in any order

Both directions work equally well:
- Forward: `"if A then B"`
- Backward: `"B if A"`

The tool generates both variations and searches with each.

### 6. Include conditions when relevant

If your lemma has preconditions, include them:

```
"x <= z / y if x * y <= z and y > 0"
```

This is better than just:
```
"x <= z / y"
```

Because it captures the complete logical relationship.

### 7. Use semantic search (embeddings)

For best results, ensure your index was built with `--embeddings`:

```bash
uv run verus-lemma-finder index scip_file.json --embeddings
```

Without embeddings, the tool falls back to keyword matching, which is less effective for mathematical queries.

### 8. Try rephrasing if needed

If you don't get good results, try:
- Adding more context
- Using different words
- Being more specific about the relationship

**Example progression:**
1. `"division"` → too vague
2. `"division by multiplication"` → better
3. `"if a * b <= c then a <= c / b"` → best!

## Understanding Search Results

The tool shows:
- **Score**: Higher is better (0-1 for semantic search, varies for keyword search)
- **Name**: The lemma name
- **Location**: File and line number
- **Documentation**: Human-readable description
- **Signature**: The actual function signature
- **Requires/Ensures**: The formal specifications

## Advanced: Interactive Mode

For exploration, use interactive mode:

```bash
uv run verus-lemma-finder interactive lemma_index.json
```

This lets you:
- Try multiple queries quickly
- Compare different phrasings
- See detailed lemma information

## Troubleshooting

### "No results found"

Try:
1. Simplifying your query
2. Using more common mathematical terms
3. Checking if your lemma index includes the relevant files
4. Regenerating the index with `--embeddings`

### "Wrong lemmas in results"

This could mean:
1. Your query is too vague (add more specifics)
2. The lemma you want has different terminology than expected
3. The index doesn't include the lemma (check the indexed paths)

### "Similar queries give different results"

If you regenerated code recently:
1. Regenerate your lemma index with the latest code
2. Ensure embeddings are enabled
3. Check that sentence-transformers is installed

```bash
uv sync  # Installs all dependencies
```

## Examples from Real Use

### Finding division/multiplication lemmas:

**Query**: `"if a times b <= c then a <= c div b"`

**Expected top result**: `lemma_mul_le_implies_div_le`

### Finding modular arithmetic lemmas:

**Query**: `"x mod m < m if m > 0"`

**Expected results**: Lemmas about modular bounds

### Finding commutative properties:

**Query**: `"a * b = b * a"`

**Expected results**: Lemmas about commutativity

### Finding distributive properties:

**Query**: `"a * (b + c) = a * b + a * c"`

**Expected results**: Lemmas about distributivity

## Quick Reference: Query Normalization Pipeline

Your query goes through these steps:

```
Original query: "if a times b <= c then a <= c div b"
      ↓
Operator normalization: "if a * b <= c then a <= c / b"
      ↓
Variable normalization: "if var1 * var2 <= var3 then var1 <= var3 / var2"
      ↓
Variation generation: 
  - "if var1 * var2 <= var3 then var1 <= var3 / var2"
  - "var1 <= var3 / var2 if var1 * var2 <= var3"
      ↓
Semantic embedding (for each variation)
      ↓
Similarity search against indexed lemmas
      ↓
Result combination (best score for each lemma)
      ↓
Top-k results returned
```

## Need Help?

If you're not getting good results, you can:
1. Check the normalization output with `test_query_normalization.py`
2. Look at the generated variations
3. See what the tool is actually searching for
4. Report issues with specific examples
