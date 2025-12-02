"""
Utility functions for the lemma finder.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

# Type checking imports (for static analysis only)
if TYPE_CHECKING:
    import numpy as np
    from sentence_transformers import SentenceTransformer

# Runtime imports for optional dependencies - embeddings
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    np = None  # type: ignore

# Runtime imports for optional dependencies - Rust parser
try:
    import verus_parser
    VERUS_PARSER_AVAILABLE = True
except ImportError:
    VERUS_PARSER_AVAILABLE = False
    verus_parser = None  # type: ignore

class ModelCache:
    """
    Thread-safe singleton cache for sentence transformer models.

    This class manages a single instance of the sentence transformer model
    to avoid reloading it multiple times (~500MB and several seconds per load).
    """

    _instance: Optional["ModelCache"] = None
    _model: Any | None = None
    _model_name: str | None = None

    def __new__(cls) -> "ModelCache":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_model(cls, model_name: str = "all-MiniLM-L6-v2") -> Any | None:
        """
        Get or load the sentence transformer model (cached).

        Args:
            model_name: Name of the sentence transformer model to load

        Returns:
            The loaded model, or None if embeddings are not available
        """
        if not EMBEDDINGS_AVAILABLE:
            return None

        # Load model if not cached or if different model requested
        if cls._model is None or cls._model_name != model_name:
            print(f"Loading sentence transformer model: {model_name}...")
            cls._model = SentenceTransformer(model_name)
            cls._model_name = model_name
            print("✓ Model loaded")

        return cls._model

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the cached model (useful for testing or memory management).

        This allows the model to be garbage collected and memory to be freed.
        """
        cls._model = None
        cls._model_name = None

    @classmethod
    def is_cached(cls) -> bool:
        """Check if a model is currently cached."""
        return cls._model is not None


def get_sentence_transformer_model(model_name: str = "all-MiniLM-L6-v2") -> Any | None:
    """
    Get or load the sentence transformer model (cached).

    This function provides backward compatibility with the previous module-level
    cache implementation. It delegates to ModelCache.get_model().

    This avoids reloading the model for each LemmaSearcher/LemmaIndexer instance,
    which saves memory and time (~500MB and several seconds).

    Args:
        model_name: Name of the sentence transformer model to load

    Returns:
        The loaded model, or None if embeddings are not available
    """
    return ModelCache.get_model(model_name)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def validate_index_file(index_file: Path) -> bool:
    """Validate that an index file exists and is readable"""
    # Could add more validation (e.g., check JSON format)
    return index_file.exists() and index_file.is_file()


def validate_scip_file(scip_file: Path) -> bool:
    """Validate that a SCIP file exists and is readable"""
    # Could add more validation
    return scip_file.exists() and scip_file.is_file()
