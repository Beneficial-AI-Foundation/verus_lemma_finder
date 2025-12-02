"""
Specification extraction from Verus source files.

This module extracts requires/ensures clauses from Verus functions.
It uses the `verus_parser` Rust module (via verus_syn) for accurate parsing,
with a regex-based fallback for when the Rust module isn't available.
"""

import re
from functools import lru_cache
from pathlib import Path

from .config import Config, get_config

# Try to import the Rust-based parser
try:
    import verus_parser

    VERUS_PARSER_AVAILABLE = True
except ImportError:
    VERUS_PARSER_AVAILABLE = False


class SpecExtractor:
    """Extract requires/ensures clauses from Verus source files"""

    def __init__(self, repo_root: Path, config: Config | None = None):
        self.repo_root = repo_root
        self.config = config if config is not None else get_config()
        # Create a bound method for the cached file reader
        self._cached_read = lru_cache(maxsize=self.config.extraction.max_cached_files)(
            self._read_file_uncached
        )

    def _read_file_uncached(self, file_path: str) -> str:
        """
        Read file content without caching (wrapped by LRU cache).

        Includes path validation to prevent directory traversal attacks.
        """
        full_path = (self.repo_root / file_path).resolve()
        repo_root_resolved = self.repo_root.resolve()

        # Security check: ensure the resolved path is within repo_root
        try:
            full_path.relative_to(repo_root_resolved)
        except ValueError:
            # Path is outside repo_root - potential security issue
            print(f"⚠️  Warning: Attempted to access file outside repo root: {file_path}")
            return ""

        if full_path.exists() and full_path.is_file():
            return full_path.read_text()
        return ""

    def _get_file_content(self, file_path: str) -> str:
        """
        Get cached file contents with LRU eviction.

        Uses functools.lru_cache to automatically manage memory,
        evicting least recently used files when cache is full.
        """
        return self._cached_read(file_path)

    def extract_specs_for_function(
        self, file_path: str, function_name: str
    ) -> tuple[list[str], list[str], int | None]:
        """
        Extract requires and ensures clauses for a function.

        Uses verus_parser (Rust + verus_syn) for accurate parsing if available,
        falls back to regex-based extraction otherwise.

        Returns: (requires_list, ensures_list, line_number)
        """
        # Validate inputs
        if not file_path or not isinstance(file_path, str):
            return [], [], None
        if not function_name or not isinstance(function_name, str):
            return [], [], None

        content = self._get_file_content(file_path)
        if not content:
            return [], [], None

        # Try Rust-based parser first (more accurate)
        if VERUS_PARSER_AVAILABLE:
            return self._extract_specs_with_verus_parser(content, function_name)

        # Fallback to regex-based extraction
        return self._extract_specs_with_regex(content, function_name)

    def _extract_specs_with_verus_parser(
        self, content: str, function_name: str
    ) -> tuple[list[str], list[str], int | None]:
        """
        Extract specs using the Rust verus_parser module.

        This uses verus_syn for proper AST-based parsing of Verus syntax.
        """
        try:
            specs = verus_parser.extract_function_specs(content, function_name)

            # Check for errors
            if specs.get("parse_error"):
                # Fall back to regex on parse error
                return self._extract_specs_with_regex(content, function_name)

            requires = specs.get("requires", [])
            ensures = specs.get("ensures", [])
            line_number = specs.get("line_number")

            return requires, ensures, line_number

        except Exception:
            # On any error, fall back to regex
            return self._extract_specs_with_regex(content, function_name)

    def _extract_specs_with_regex(
        self, content: str, function_name: str
    ) -> tuple[list[str], list[str], int | None]:
        """
        Extract specs using regex-based parsing (fallback method).

        This is less accurate but works without the Rust module.
        """
        # Find the function definition
        # Pattern: pub proof fn function_name(...) or pub fn function_name(...)
        pattern = rf"(?:pub\s+)?(?:proof\s+)?fn\s+{re.escape(function_name)}\s*\("

        match = re.search(pattern, content)
        if not match:
            return [], [], None

        # Calculate line number
        line_number = content[: match.start()].count("\n") + 1

        # Extract everything from function definition to the opening brace
        start = match.start()

        # Find the opening brace
        brace_pos = content.find("{", start)
        if brace_pos == -1:
            return [], [], line_number

        func_header = content[start:brace_pos]

        # Extract requires clauses
        requires = self._extract_clauses(func_header, "requires")

        # Extract ensures clauses
        ensures = self._extract_clauses(func_header, "ensures")

        return requires, ensures, line_number

    def _extract_clauses(self, text: str, keyword: str) -> list[str]:
        """Extract requires or ensures clauses"""
        clauses = []

        # Find the keyword
        pattern = rf"\b{keyword}\b"
        match = re.search(pattern, text)

        if not match:
            return []

        # Extract everything after the keyword until we hit 'ensures', 'decreases', '{', or another keyword
        start = match.end()
        remaining = text[start:]

        # Find the end of this clause section
        # It ends at: ensures, decreases, {, or recommends
        end_markers = ["ensures", "decreases", "recommends", "{"]
        end_pos = len(remaining)

        for marker in end_markers:
            if marker == keyword:
                continue
            marker_match = re.search(rf"\b{marker}\b", remaining)
            if marker_match:
                end_pos = min(end_pos, marker_match.start())

        clause_text = remaining[:end_pos].strip()

        # Split by commas, but be careful with nested structures
        # For now, simple split - could be improved with proper parsing
        if clause_text:
            # Remove trailing comma
            clause_text = clause_text.rstrip(",")
            # Split into individual clauses (simple version)
            # In practice, would need better parsing for nested expressions
            clauses = [c.strip() for c in clause_text.split(",") if c.strip()]

        return clauses
