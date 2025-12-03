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

    # Simple API for finding similar lemmas (recommended for integration)
    from verus_lemma_finder import get_similar_lemmas, load_searcher

    results = get_similar_lemmas("lemma_mod_bound", index_path="lemma_index.json")

    # Find lemmas similar to an existing lemma (by name)
    from verus_lemma_finder import get_similar_to_lemma

    results = get_similar_to_lemma("lemma_mod_bound", index_path="lemma_index.json")
"""

__version__ = "1.1.0"

# Public API
from .api import (
    SimilarLemma,
    get_similar_lemmas,
    get_similar_lemmas_dict,
    get_similar_to_lemma,
    get_similar_to_lemma_dict,
    load_searcher,
)
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
    # Simple API (recommended for integration)
    "get_similar_lemmas",
    "get_similar_lemmas_dict",
    "get_similar_to_lemma",
    "get_similar_to_lemma_dict",
    "load_searcher",
    "SimilarLemma",
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
