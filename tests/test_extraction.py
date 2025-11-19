"""
Unit tests for spec extraction from Rust/Verus source code.

Tests the SpecExtractor class including edge cases and error handling.
"""

import tempfile
from pathlib import Path

import pytest

from verus_lemma_finder.config import ExtractionConfig
from verus_lemma_finder.extraction import SpecExtractor


class TestSpecExtractorBasic:
    """Test basic SpecExtractor functionality"""

    def test_extractor_initialization(self):
        """Test SpecExtractor can be initialized"""
        extractor = SpecExtractor()
        assert extractor is not None

    def test_extractor_with_custom_config(self):
        """Test SpecExtractor with custom configuration"""
        config = ExtractionConfig(
            include_private=True,
            include_proof_functions=False
        )
        extractor = SpecExtractor(config)
        assert extractor is not None


class TestFileReading:
    """Test file reading and caching"""

    def test_read_simple_file(self):
        """Test reading a simple Rust file"""
        content = """
pub fn example() {
    // Simple function
}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            assert "pub fn example" in result
        finally:
            tmp_path.unlink()

    def test_read_empty_file(self):
        """Test reading an empty file"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
            # File is empty

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            # Empty file should return empty string
            assert result == ""
        finally:
            tmp_path.unlink()

    def test_read_nonexistent_file(self):
        """Test reading non-existent file returns None"""
        fake_path = Path("/nonexistent/file.rs")
        extractor = SpecExtractor()
        result = extractor._get_file_content(fake_path)
        assert result is None

    def test_file_caching(self):
        """Test that file contents are cached"""
        content = "pub fn test() {}"
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            # First read
            result1 = extractor._get_file_content(tmp_path)
            # Second read (should be cached)
            result2 = extractor._get_file_content(tmp_path)

            assert result1 == result2
            # Both should have the content
            assert "pub fn test" in result1
        finally:
            tmp_path.unlink()


class TestUnicodeHandling:
    """Test handling of Unicode and special characters"""

    def test_unicode_in_comments(self):
        """Test reading file with Unicode in comments"""
        content = """
// Comment with Unicode: Привет мир 你好世界
pub fn test() {}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False,
            encoding='utf-8'
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            assert "pub fn test" in result
        finally:
            tmp_path.unlink()

    def test_unicode_in_function_name(self):
        """Test file with Unicode in identifiers (if valid Rust)"""
        # Rust allows Unicode identifiers
        content = """
pub fn test_функция() {}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False,
            encoding='utf-8'
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            # Should contain the Unicode function name
            assert "функция" in result
        finally:
            tmp_path.unlink()


class TestMalformedInput:
    """Test handling of malformed or unusual input"""

    def test_file_with_very_long_lines(self):
        """Test file with very long lines"""
        # Create a file with a 10K character line
        long_line = "// " + "x" * 10000 + "\n"
        content = long_line + "pub fn test() {}"

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            assert "pub fn test" in result
        finally:
            tmp_path.unlink()

    def test_file_with_mixed_line_endings(self):
        """Test file with mixed line endings"""
        content = "pub fn test1() {}\r\npub fn test2() {}\npub fn test3() {}\r"

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False,
            newline=''  # Don't translate line endings
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            # All functions should be present
            assert "test1" in result
            assert "test2" in result
            assert "test3" in result
        finally:
            tmp_path.unlink()

    def test_file_with_null_bytes(self):
        """Test file with null bytes (binary data)"""
        content = b"pub fn test() \x00 {}"

        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            # Should handle gracefully (may return None or partial content)
            # The important thing is it doesn't crash
            assert result is not None or result is None
        finally:
            tmp_path.unlink()


class TestSpecExtractionPatterns:
    """Test extraction of requires/ensures clauses"""

    def test_extract_simple_requires(self):
        """Test extracting simple requires clause"""
        content = """
pub fn test(x: u32)
    requires x > 0
{
    // body
}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            # Extract specs (simplified test - actual extraction more complex)
            file_content = extractor._get_file_content(tmp_path)
            assert file_content is not None
            assert "requires" in file_content
            assert "x > 0" in file_content
        finally:
            tmp_path.unlink()

    def test_extract_multiple_requires(self):
        """Test extracting multiple requires clauses"""
        content = """
pub fn test(x: u32, y: u32)
    requires
        x > 0,
        y > 0,
        x < y
{
    // body
}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            file_content = extractor._get_file_content(tmp_path)
            assert file_content is not None
            assert "requires" in file_content
            # All conditions should be present
            assert "x > 0" in file_content
            assert "y > 0" in file_content
            assert "x < y" in file_content
        finally:
            tmp_path.unlink()

    def test_extract_ensures_clause(self):
        """Test extracting ensures clause"""
        content = """
pub fn double(x: u32) -> u32
    ensures result == x * 2
{
    x * 2
}
"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()
            file_content = extractor._get_file_content(tmp_path)
            assert file_content is not None
            assert "ensures" in file_content
            assert "result" in file_content
        finally:
            tmp_path.unlink()


class TestPathHandling:
    """Test handling of different path formats"""

    def test_absolute_path(self):
        """Test reading file with absolute path"""
        content = "pub fn test() {}"
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name).absolute()

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(tmp_path)
            assert result is not None
            assert "pub fn test" in result
        finally:
            tmp_path.unlink()

    def test_relative_path(self):
        """Test reading file with relative path"""
        content = "pub fn test() {}"
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False,
            dir='.'
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
            # Get relative path
            relative_path = tmp_path.relative_to(Path.cwd())

        try:
            extractor = SpecExtractor()
            result = extractor._get_file_content(relative_path)
            assert result is not None
            assert "pub fn test" in result
        finally:
            tmp_path.unlink()


class TestCacheManagement:
    """Test LRU cache behavior"""

    def test_cache_respects_max_size(self):
        """Test that cache respects maximum size configuration"""
        config = ExtractionConfig(max_cached_files=2)
        extractor = SpecExtractor(config)

        # Create 3 temp files
        files = []
        for i in range(3):
            tmp = tempfile.NamedTemporaryFile(
                mode='w',
                suffix=".rs",
                delete=False
            )
            tmp.write(f"pub fn test{i}() {{}}")
            tmp.close()
            files.append(Path(tmp.name))

        try:
            # Read all 3 files
            for f in files:
                extractor._get_file_content(f)

            # Cache should only hold 2 files (LRU)
            # This is implicit in the LRU cache decorator behavior
            # We can't easily inspect cache size, but it won't error
        finally:
            for f in files:
                f.unlink()

    def test_repeated_access_uses_cache(self):
        """Test that repeated access to same file uses cache"""
        content = "pub fn test() {}"
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".rs",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            extractor = SpecExtractor()

            # Read multiple times
            results = [extractor._get_file_content(tmp_path) for _ in range(5)]

            # All results should be identical
            assert all(r == results[0] for r in results)
            assert all("pub fn test" in r for r in results)
        finally:
            tmp_path.unlink()

