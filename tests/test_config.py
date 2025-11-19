"""
Unit tests for configuration management.

Tests the Config classes for search, indexing, and extraction.
"""

import pytest

from verus_lemma_finder.config import Config, ExtractionConfig, IndexingConfig, SearchConfig


class TestSearchConfig:
    """Test SearchConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = SearchConfig()
        assert config.top_k == 10
        assert config.semantic_weight == 0.7
        assert config.keyword_weight == 0.3
        assert config.min_score == 0.0
        assert config.normalize_query is True

    def test_custom_values(self):
        """Test custom configuration values"""
        config = SearchConfig(
            top_k=5,
            semantic_weight=0.5,
            keyword_weight=0.5,
            min_score=0.1,
            normalize_query=False
        )
        assert config.top_k == 5
        assert config.semantic_weight == 0.5
        assert config.keyword_weight == 0.5
        assert config.min_score == 0.1
        assert config.normalize_query is False

    def test_weight_sum(self):
        """Test that semantic and keyword weights sum to 1.0"""
        config = SearchConfig(semantic_weight=0.6, keyword_weight=0.4)
        assert abs(config.semantic_weight + config.keyword_weight - 1.0) < 0.01


class TestIndexingConfig:
    """Test IndexingConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = IndexingConfig()
        assert config.generate_embeddings is True
        assert config.model_name == "all-MiniLM-L6-v2"
        assert config.normalize_lemma_text is True
        assert config.batch_size == 32

    def test_custom_values(self):
        """Test custom configuration values"""
        config = IndexingConfig(
            generate_embeddings=False,
            model_name="custom-model",
            normalize_lemma_text=False,
            batch_size=16
        )
        assert config.generate_embeddings is False
        assert config.model_name == "custom-model"
        assert config.normalize_lemma_text is False
        assert config.batch_size == 16

    def test_batch_size_positive(self):
        """Test that batch size is positive"""
        config = IndexingConfig(batch_size=10)
        assert config.batch_size > 0


class TestExtractionConfig:
    """Test ExtractionConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = ExtractionConfig()
        assert config.include_private is False
        assert config.include_proof_functions is True
        assert config.include_exec_functions is True
        assert config.max_cached_files == 128

    def test_custom_values(self):
        """Test custom configuration values"""
        config = ExtractionConfig(
            include_private=True,
            include_proof_functions=False,
            include_exec_functions=False,
            max_cached_files=64
        )
        assert config.include_private is True
        assert config.include_proof_functions is False
        assert config.include_exec_functions is False
        assert config.max_cached_files == 64

    def test_cache_size_positive(self):
        """Test that cache size is positive"""
        config = ExtractionConfig(max_cached_files=256)
        assert config.max_cached_files > 0


class TestMainConfig:
    """Test main Config class"""

    def test_default_nested_configs(self):
        """Test that nested configs are initialized with defaults"""
        config = Config()
        assert isinstance(config.search, SearchConfig)
        assert isinstance(config.indexing, IndexingConfig)
        assert isinstance(config.extraction, ExtractionConfig)

    def test_nested_config_values(self):
        """Test accessing nested config values"""
        config = Config()
        assert config.search.top_k == 10
        assert config.indexing.model_name == "all-MiniLM-L6-v2"
        assert config.extraction.include_private is False

    def test_custom_nested_configs(self):
        """Test custom nested configurations"""
        custom_search = SearchConfig(top_k=20)
        custom_indexing = IndexingConfig(batch_size=64)
        custom_extraction = ExtractionConfig(include_private=True)

        config = Config(
            search=custom_search,
            indexing=custom_indexing,
            extraction=custom_extraction
        )

        assert config.search.top_k == 20
        assert config.indexing.batch_size == 64
        assert config.extraction.include_private is True

    def test_config_immutability_via_dataclass(self):
        """Test that config can be modified (dataclass is mutable by default)"""
        config = Config()
        original_top_k = config.search.top_k
        config.search.top_k = 15
        assert config.search.top_k == 15
        assert config.search.top_k != original_top_k


class TestConfigIntegration:
    """Test configuration usage in realistic scenarios"""

    def test_search_config_for_semantic_only(self):
        """Test configuration for semantic-only search"""
        config = SearchConfig(
            semantic_weight=1.0,
            keyword_weight=0.0
        )
        assert config.semantic_weight == 1.0
        assert config.keyword_weight == 0.0

    def test_search_config_for_keyword_only(self):
        """Test configuration for keyword-only search"""
        config = SearchConfig(
            semantic_weight=0.0,
            keyword_weight=1.0
        )
        assert config.semantic_weight == 0.0
        assert config.keyword_weight == 1.0

    def test_indexing_config_without_embeddings(self):
        """Test configuration for indexing without embeddings"""
        config = IndexingConfig(generate_embeddings=False)
        assert config.generate_embeddings is False
        # Model name should still be set even if not generating embeddings
        assert config.model_name is not None

    def test_extraction_config_all_functions(self):
        """Test configuration for extracting all functions"""
        config = ExtractionConfig(
            include_private=True,
            include_proof_functions=True,
            include_exec_functions=True
        )
        assert config.include_private is True
        assert config.include_proof_functions is True
        assert config.include_exec_functions is True

    def test_extraction_config_public_proof_only(self):
        """Test configuration for public proof functions only"""
        config = ExtractionConfig(
            include_private=False,
            include_proof_functions=True,
            include_exec_functions=False
        )
        assert config.include_private is False
        assert config.include_proof_functions is True
        assert config.include_exec_functions is False

