# Configuration Guide

Verus Lemma Finder uses a flexible, type-safe configuration system based on Python dataclasses. You can use the default configuration or customize behavior through a JSON configuration file.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Configuration Sections](#configuration-sections)
  - [Search Configuration](#search-configuration)
  - [Indexing Configuration](#indexing-configuration)
  - [Extraction Configuration](#extraction-configuration)
- [Usage Examples](#usage-examples)
- [Python API](#python-api)
- [Advanced Usage](#advanced-usage)

---

## 🚀 Quick Start

### Using Defaults (No Config File Needed)

The tool works out-of-the-box with sensible defaults:

```bash
# Just use the tool normally
uv run python -m verus_lemma_finder search "query" index.json
```

### Using a Custom Config File

Create a `verus_lemma_finder.config.json` in your project root:

```json
{
  "search": {
    "keyword_weight": 0.3,
    "semantic_weight": 0.7,
    "default_top_k": 10
  },
  "indexing": {
    "lemma_file_keywords": ["lemmas", "specs"],
    "lemma_function_prefixes": ["lemma_", "axiom_"]
  },
  "extraction": {
    "max_cached_files": 256
  }
}
```

The tool automatically loads this file if it exists.

---

## ⚙️ Configuration Sections

### Search Configuration

Controls how lemma search behaves.

```json
{
  "search": {
    "keyword_weight": 0.3,
    "semantic_weight": 0.7,
    "default_top_k": 10,
    "name_match_boost": 2.0,
    "doc_match_boost": 1.5,
    "embedding_model": "all-MiniLM-L6-v2"
  }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keyword_weight` | float | 0.3 | Weight for keyword matching in hybrid search (0-1) |
| `semantic_weight` | float | 0.7 | Weight for semantic similarity in hybrid search (0-1) |
| `default_top_k` | int | 10 | Default number of results to return |
| `name_match_boost` | float | 2.0 | Score multiplier for matches in lemma name |
| `doc_match_boost` | float | 1.5 | Score multiplier for matches in documentation |
| `embedding_model` | string | "all-MiniLM-L6-v2" | Sentence transformer model to use |

**Tips:**
- Increase `keyword_weight` for more exact matching
- Increase `semantic_weight` for more conceptual matching
- Adjust boost values to prioritize name or documentation matches

### Indexing Configuration

Controls how lemmas are indexed from SCIP data.

```json
{
  "indexing": {
    "embedding_model": "all-MiniLM-L6-v2",
    "lemma_file_keywords": ["lemmas", "specs", "field.rs", "scalar.rs"],
    "lemma_function_prefixes": ["lemma_", "axiom_", "spec_", "proof_"],
    "scip_function_kind": 17,
    "scip_definition_role": 1
  }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `embedding_model` | string | "all-MiniLM-L6-v2" | Model for generating embeddings |
| `lemma_file_keywords` | array | ["lemmas", "specs", ...] | File path keywords indicating lemma files |
| `lemma_function_prefixes` | array | ["lemma_", "axiom_", ...] | Function name prefixes that indicate lemmas |
| `scip_function_kind` | int | 17 | SCIP kind code for functions |
| `scip_definition_role` | int | 1 | SCIP role code for definitions |

**Tips:**
- Add custom file keywords if your project uses different naming conventions
- Add custom function prefixes for project-specific lemma naming
- SCIP constants should generally not be changed

### Extraction Configuration

Controls specification extraction from source files.

```json
{
  "extraction": {
    "max_cached_files": 128
  }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_cached_files` | int | 128 | Maximum files to cache in memory (LRU cache size) |

**Tips:**
- Increase for large projects with many lemmas
- Decrease to reduce memory usage

---

## 💡 Usage Examples

### Example 1: More Semantic Search

If you want more "fuzzy" semantic matching:

```json
{
  "search": {
    "keyword_weight": 0.2,
    "semantic_weight": 0.8
  }
}
```

### Example 2: More Exact Matching

If you want more exact keyword matching:

```json
{
  "search": {
    "keyword_weight": 0.5,
    "semantic_weight": 0.5
  }
}
```

### Example 3: Custom Lemma Naming Convention

If your project uses different naming:

```json
{
  "indexing": {
    "lemma_function_prefixes": ["theorem_", "prop_", "lemma_", "axiom_"]
  }
}
```

### Example 4: Larger Cache for Big Projects

```json
{
  "extraction": {
    "max_cached_files": 512
  }
}
```

---

## 🐍 Python API

### Basic Usage

```python
from verus_lemma_finder import LemmaSearcher, get_config

# Use default config
searcher = LemmaSearcher("index.json")

# Or get config explicitly
config = get_config()
print(f"Keyword weight: {config.search.keyword_weight}")
```

### Custom Config File

```python
from pathlib import Path
from verus_lemma_finder import LemmaSearcher, get_config

# Load from custom path
config = get_config(Path("my_custom_config.json"))

# Use with searcher
searcher = LemmaSearcher("index.json", config=config)
```

### Programmatic Configuration

```python
from verus_lemma_finder import Config, SearchConfig, LemmaSearcher

# Create config programmatically
config = Config(
    search=SearchConfig(
        keyword_weight=0.5,
        semantic_weight=0.5,
        default_top_k=20
    )
)

# Use with searcher
searcher = LemmaSearcher("index.json", config=config)
```

### Modify and Save Config

```python
from verus_lemma_finder import get_config
from pathlib import Path

# Get default config
config = get_config()

# Modify values
config.search.keyword_weight = 0.4
config.search.semantic_weight = 0.6

# Save to file
config.save_to_file(Path("my_config.json"))
```

---

## 🔧 Advanced Usage

### Reload Configuration

```python
from verus_lemma_finder import get_config, reset_config

# First load
config1 = get_config()

# Modify config file...

# Reload from file
reset_config()
config2 = get_config()  # Fresh load
```

### Validation

Configuration is automatically validated when loaded:

```python
from verus_lemma_finder import SearchConfig

# This will raise ValueError
try:
    config = SearchConfig(keyword_weight=1.5)  # Must be in [0, 1]
    config.validate()
except ValueError as e:
    print(f"Invalid config: {e}")
```

### Per-Instance Config

Different instances can use different configs:

```python
from verus_lemma_finder import LemmaSearcher, Config, SearchConfig

# Searcher for fuzzy matching
fuzzy_config = Config(search=SearchConfig(keyword_weight=0.2))
fuzzy_searcher = LemmaSearcher("index.json", config=fuzzy_config)

# Searcher for exact matching
exact_config = Config(search=SearchConfig(keyword_weight=0.6))
exact_searcher = LemmaSearcher("index.json", config=exact_config)
```

### Export Configuration

```python
from verus_lemma_finder import get_config

config = get_config()

# Get as dictionary
config_dict = config.to_dict()
print(config_dict)

# Prints:
# {
#   'search': {'keyword_weight': 0.3, ...},
#   'indexing': {'embedding_model': '...', ...},
#   'extraction': {'max_cached_files': 128}
# }
```

---

## 🎯 Configuration Best Practices

1. **Start with defaults** - They work well for most cases
2. **Tune incrementally** - Change one parameter at a time and observe results
3. **Document changes** - Add comments in config files explaining why you changed values
4. **Project-specific** - Keep config files in project root, not global
5. **Version control** - Commit your config file so team members use same settings

---

## 📚 Related Documentation

- [Search Tips](search-tips.md) - How to write effective queries
- [Testing Guide](testing.md) - How to test with custom configurations
- [Architecture](lemma-search-design.md) - How configuration fits into the system

---

## 🐛 Troubleshooting

### Config file not loading

**Problem**: Your config file exists but defaults are being used.

**Solution**: Ensure the file is named exactly `verus_lemma_finder.config.json` and is in the current working directory.

```bash
# Check current directory
pwd
ls -la verus_lemma_finder.config.json
```

### Invalid configuration error

**Problem**: Tool fails to start with validation error.

**Solution**: Check your config file syntax and value ranges:
- Weights must be in [0, 1]
- Counts must be positive integers
- Arrays must not be empty

### Performance issues

**Problem**: Slow search or high memory usage.

**Solution**: Adjust these parameters:
- Decrease `max_cached_files` to reduce memory
- Decrease `default_top_k` to return fewer results
- Use keyword-only search (set `semantic_weight=0`) if embeddings are slow

---

**Questions?** Open an issue or check the [main README](../README.md).

