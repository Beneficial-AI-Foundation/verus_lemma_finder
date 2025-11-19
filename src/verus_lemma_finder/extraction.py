"""
Specification extraction from Verus source files.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config, get_config


class SpecExtractor:
    """Extract requires/ensures clauses from Verus source files"""

    def __init__(self, repo_root: Path, config: Optional[Config] = None):
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
            print(
                f"⚠️  Warning: Attempted to access file outside repo root: {file_path}"
            )
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
    ) -> Tuple[List[str], List[str], Optional[int]]:
        """
        Extract requires and ensures clauses for a function.
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

    def _extract_clauses(self, text: str, keyword: str) -> List[str]:
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
