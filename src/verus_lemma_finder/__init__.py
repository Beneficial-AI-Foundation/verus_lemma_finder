"""
Verus Lemma Finder - Semantic search for Verus lemmas.

This package provides tools for indexing and searching Verus lemmas using
semantic search powered by sentence transformers.

Example usage:
    from verus_lemma_finder import LemmaSearcher, LemmaIndexer

    # Search for lemmas
    searcher = LemmaSearcher("lemma_index.json")
    results = searcher.search("if a * b <= c then a <= c / b")

    # Build an index
    indexer = LemmaIndexer("scip_data.json", ".", use_embeddings=True)
    indexer.build_index()
    indexer.save_index("lemma_index.json")
"""

__version__ = "1.0.0"

# Public API
from .config import (
    Config,
    ExtractionConfig,
    IndexingConfig,
    SearchConfig,
    get_config,
    reset_config,
)
from .extraction import SpecExtractor
from .indexing import LemmaIndexer, merge_indexes
from .models import LemmaInfo
from .normalization import QueryNormalizer
from .scip_utils import check_command_available, clone_verus_repo, generate_scip_json
from .search import LemmaSearcher
from .utils import ModelCache

__all__ = [
    # Core classes
    "LemmaInfo",
    "LemmaSearcher",
    "LemmaIndexer",
    "SpecExtractor",
    "QueryNormalizer",
    "ModelCache",
    # Configuration
    "Config",
    "SearchConfig",
    "IndexingConfig",
    "ExtractionConfig",
    "get_config",
    "reset_config",
    # Utility functions
    "merge_indexes",
    "generate_scip_json",
    "clone_verus_repo",
    "check_command_available",
    # Version
    "__version__",
]
