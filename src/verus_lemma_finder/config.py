"""
Configuration management for Verus Lemma Finder.

This module provides a centralized, type-safe configuration system using dataclasses.
Configuration can be loaded from a JSON file or used with defaults.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SearchConfig:
    """Configuration for lemma search behavior."""

    # Hybrid search weights (should sum to ~1.0)
    keyword_weight: float = 0.3  # 30% keyword matching weight
    semantic_weight: float = 0.7  # 70% semantic similarity weight

    # Search parameters
    default_top_k: int = 10  # Default number of results to return

    # Score boosting factors
    name_match_boost: float = 2.0  # Score multiplier for matches in lemma name
    doc_match_boost: float = 1.5  # Score multiplier for matches in documentation

    # Model configuration
    embedding_model: str = "all-MiniLM-L6-v2"  # Lightweight but effective model

    def validate(self) -> None:
        """Validate configuration values."""
        if not 0 <= self.keyword_weight <= 1:
            raise ValueError(
                f"keyword_weight must be in [0, 1], got {self.keyword_weight}"
            )
        if not 0 <= self.semantic_weight <= 1:
            raise ValueError(
                f"semantic_weight must be in [0, 1], got {self.semantic_weight}"
            )
        if self.default_top_k < 1:
            raise ValueError(f"default_top_k must be >= 1, got {self.default_top_k}")
        if self.name_match_boost < 0:
            raise ValueError(
                f"name_match_boost must be >= 0, got {self.name_match_boost}"
            )
        if self.doc_match_boost < 0:
            raise ValueError(
                f"doc_match_boost must be >= 0, got {self.doc_match_boost}"
            )


@dataclass
class IndexingConfig:
    """Configuration for lemma indexing from SCIP data."""

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"  # Lightweight but effective model

    # File filtering
    lemma_file_keywords: List[str] = field(
        default_factory=lambda: ["lemmas", "specs", "field.rs", "scalar.rs"]
    )  # Files likely to contain lemmas

    # Function filtering
    lemma_function_prefixes: List[str] = field(
        default_factory=lambda: ["lemma_", "axiom_", "spec_", "proof_"]
    )  # Function prefixes that indicate lemmas

    # SCIP constants (from SCIP protocol specification)
    scip_function_kind: int = 17  # SCIP kind code for functions
    scip_definition_role: int = (
        1  # SCIP symbol_roles value for definitions (not references)
    )

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.lemma_file_keywords:
            raise ValueError("lemma_file_keywords cannot be empty")
        if not self.lemma_function_prefixes:
            raise ValueError("lemma_function_prefixes cannot be empty")


@dataclass
class ExtractionConfig:
    """Configuration for specification extraction from source files."""

    # Cache configuration
    max_cached_files: int = 128  # Maximum number of files to keep in LRU cache

    def validate(self) -> None:
        """Validate configuration values."""
        if self.max_cached_files < 1:
            raise ValueError(
                f"max_cached_files must be >= 1, got {self.max_cached_files}"
            )


@dataclass
class Config:
    """
    Main configuration for Verus Lemma Finder.

    This configuration can be used with defaults or loaded from a JSON file.

    Example JSON file (verus_lemma_finder.config.json):
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
    """

    search: SearchConfig = field(default_factory=SearchConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    def validate(self) -> None:
        """Validate all configuration sections."""
        self.search.validate()
        self.indexing.validate()
        self.extraction.validate()

    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """
        Load configuration from a JSON file.

        Args:
            config_path: Path to the JSON configuration file

        Returns:
            Config instance with values from file (falling back to defaults for missing values)

        Raises:
            FileNotFoundError: If config_path doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            ValueError: If configuration values are invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = json.load(f)

        # Create config with partial data (missing keys use defaults)
        config = cls(
            search=SearchConfig(**data.get("search", {})),
            indexing=IndexingConfig(**data.get("indexing", {})),
            extraction=ExtractionConfig(**data.get("extraction", {})),
        )

        # Validate the loaded configuration
        config.validate()

        return config

    @classmethod
    def load_from_file_or_default(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from file if it exists, otherwise use defaults.

        Args:
            config_path: Optional path to config file. If None, looks for
                        'verus_lemma_finder.config.json' in current directory.

        Returns:
            Config instance
        """
        if config_path is None:
            config_path = Path("verus_lemma_finder.config.json")

        if config_path.exists():
            try:
                return cls.load_from_file(config_path)
            except Exception as e:
                print(f"⚠️  Warning: Failed to load config from {config_path}: {e}")
                print("   Using default configuration.")
                return cls()

        return cls()

    def save_to_file(self, config_path: Path) -> None:
        """
        Save current configuration to a JSON file.

        Args:
            config_path: Path where to save the configuration
        """
        data = {
            "search": asdict(self.search),
            "indexing": asdict(self.indexing),
            "extraction": asdict(self.extraction),
        }

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "search": asdict(self.search),
            "indexing": asdict(self.indexing),
            "extraction": asdict(self.extraction),
        }


# Global configuration instance (lazy-loaded singleton)
_config: Optional[Config] = None


def get_config(config_path: Optional[Path] = None, reload: bool = False) -> Config:
    """
    Get the global configuration instance (singleton pattern).

    Args:
        config_path: Optional path to config file. Only used on first call or if reload=True
        reload: If True, reload configuration from file even if already loaded

    Returns:
        Config instance

    Example:
        >>> config = get_config()
        >>> config.search.keyword_weight
        0.3

        >>> # Use custom config file
        >>> config = get_config(Path("my_config.json"))

        >>> # Reload configuration
        >>> config = get_config(reload=True)
    """
    global _config

    if _config is None or reload:
        _config = Config.load_from_file_or_default(config_path)

    return _config


def reset_config() -> None:
    """
    Reset the global configuration to defaults.

    Useful for testing or when you want to reload configuration.
    """
    global _config
    _config = None
