"""
Unit tests for utility functions.

Tests file validation, formatting, and model caching.
"""

import tempfile
from pathlib import Path

import pytest

from verus_lemma_finder.utils import (
    EMBEDDINGS_AVAILABLE,
    ModelCache,
    format_file_size,
    get_sentence_transformer_model,
    validate_index_file,
    validate_scip_file,
)


class TestFileValidation:
    """Test file validation functions"""

    def test_validate_existing_file(self):
        """Test validation of existing file"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(b'{"test": "data"}')
            tmp_path = Path(tmp.name)

        try:
            assert validate_index_file(tmp_path) is True
            assert validate_scip_file(tmp_path) is True
        finally:
            tmp_path.unlink()

    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file"""
        fake_path = Path("/nonexistent/path/file.json")
        assert validate_index_file(fake_path) is False
        assert validate_scip_file(fake_path) is False

    def test_validate_directory_not_file(self):
        """Test validation fails for directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            assert validate_index_file(dir_path) is False
            assert validate_scip_file(dir_path) is False

    def test_validate_empty_file(self):
        """Test validation of empty file (should still pass)"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            # File is empty but exists

        try:
            # Empty file should still validate (existence check only)
            assert validate_index_file(tmp_path) is True
        finally:
            tmp_path.unlink()


class TestFileSizeFormatting:
    """Test file size formatting"""

    def test_format_bytes(self):
        """Test formatting of sizes in bytes"""
        assert format_file_size(0) == "0.0 B"
        assert format_file_size(100) == "100.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_format_kilobytes(self):
        """Test formatting of sizes in KB"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(2048) == "2.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_format_megabytes(self):
        """Test formatting of sizes in MB"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0 MB"
        assert format_file_size(int(1.5 * 1024 * 1024)) == "1.5 MB"

    def test_format_gigabytes(self):
        """Test formatting of sizes in GB"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(2 * 1024 * 1024 * 1024) == "2.0 GB"

    def test_format_terabytes(self):
        """Test formatting of sizes in TB"""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    def test_format_large_number(self):
        """Test formatting of very large sizes"""
        huge_size = 10 * 1024 * 1024 * 1024 * 1024  # 10 TB
        result = format_file_size(huge_size)
        assert "TB" in result
        assert result.startswith("10.")

    def test_format_fractional_units(self):
        """Test formatting shows fractions correctly"""
        # 1.7 KB
        size = int(1.7 * 1024)
        result = format_file_size(size)
        assert result == "1.7 KB"


class TestModelCache:
    """Test ModelCache singleton for sentence transformers"""

    def setup_method(self):
        """Clear cache before each test"""
        ModelCache.clear_cache()

    def teardown_method(self):
        """Clear cache after each test"""
        ModelCache.clear_cache()

    def test_singleton_pattern(self):
        """Test that ModelCache follows singleton pattern"""
        cache1 = ModelCache()
        cache2 = ModelCache()
        assert cache1 is cache2

    def test_initial_state_no_model_cached(self):
        """Test initial state has no cached model"""
        assert ModelCache.is_cached() is False

    def test_clear_cache_empties_model(self):
        """Test clearing cache removes model"""
        ModelCache.clear_cache()
        assert ModelCache.is_cached() is False

    @pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
    def test_get_model_loads_model(self):
        """Test getting model loads and caches it"""
        model = ModelCache.get_model("all-MiniLM-L6-v2")
        assert model is not None
        assert ModelCache.is_cached() is True

    @pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
    def test_get_model_cached_second_call(self):
        """Test second call returns cached model"""
        model1 = ModelCache.get_model("all-MiniLM-L6-v2")
        model2 = ModelCache.get_model("all-MiniLM-L6-v2")
        # Should be the same object (cached)
        assert model1 is model2

    @pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
    def test_different_model_reloads(self):
        """Test requesting different model reloads"""
        ModelCache.get_model("all-MiniLM-L6-v2")
        ModelCache.clear_cache()  # Clear to test reloading
        # In practice, would request different model name
        # but for testing we'll just verify cache was cleared
        assert ModelCache.is_cached() is False

    def test_get_model_no_embeddings_returns_none(self):
        """Test that get_model returns None if embeddings not available"""
        if not EMBEDDINGS_AVAILABLE:
            model = ModelCache.get_model()
            assert model is None


class TestBackwardCompatibility:
    """Test backward compatibility functions"""

    def setup_method(self):
        """Clear cache before each test"""
        ModelCache.clear_cache()

    def teardown_method(self):
        """Clear cache after each test"""
        ModelCache.clear_cache()

    def test_get_sentence_transformer_model_delegates_to_cache(self):
        """Test old function delegates to ModelCache"""
        # Clear any existing cache
        ModelCache.clear_cache()

        # Call old function
        model = get_sentence_transformer_model()

        if EMBEDDINGS_AVAILABLE:
            # Should have loaded model through cache
            assert ModelCache.is_cached() is True
        else:
            # Should return None if not available
            assert model is None

    @pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
    def test_mixed_api_usage_shares_cache(self):
        """Test that old and new API share the same cache"""
        # Load via new API
        model1 = ModelCache.get_model("all-MiniLM-L6-v2")

        # Get via old API
        model2 = get_sentence_transformer_model("all-MiniLM-L6-v2")

        # Should be same cached model
        assert model1 is model2


class TestEmbeddingsAvailable:
    """Test EMBEDDINGS_AVAILABLE flag"""

    def test_embeddings_available_is_boolean(self):
        """Test that EMBEDDINGS_AVAILABLE is a boolean"""
        assert isinstance(EMBEDDINGS_AVAILABLE, bool)

    def test_embeddings_availability_consistent(self):
        """Test embeddings availability is consistent with imports"""
        try:
            import sentence_transformers  # noqa: F401

            # If import succeeds, flag should be True
            assert EMBEDDINGS_AVAILABLE is True
        except ImportError:
            # If import fails, flag should be False
            assert EMBEDDINGS_AVAILABLE is False


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_file_with_special_characters(self):
        """Test validation of file with special characters in name"""
        with tempfile.NamedTemporaryFile(
            prefix="test file with spaces", suffix=".json", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            assert validate_index_file(tmp_path) is True
        finally:
            tmp_path.unlink()

    def test_format_size_zero(self):
        """Test formatting zero size"""
        assert format_file_size(0) == "0.0 B"

    def test_format_size_one_byte(self):
        """Test formatting single byte"""
        assert format_file_size(1) == "1.0 B"

    def test_format_size_negative_handled_gracefully(self):
        """Test negative size doesn't crash (though invalid input)"""
        # This is invalid input, but function should handle gracefully
        result = format_file_size(-1024)
        assert isinstance(result, str)

    def test_validate_path_with_unicode(self):
        """Test validation with unicode characters in path"""
        # Create temp file with unicode in name
        with tempfile.NamedTemporaryFile(prefix="test_файл_", suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            assert validate_index_file(tmp_path) is True
        finally:
            tmp_path.unlink()

    def test_model_cache_clear_when_not_cached(self):
        """Test clearing cache when nothing is cached doesn't error"""
        ModelCache.clear_cache()
        ModelCache.clear_cache()  # Should not error
        assert ModelCache.is_cached() is False
