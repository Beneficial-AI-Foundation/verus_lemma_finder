"""
Data models for Verus lemma search.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LemmaInfo:
    """Structured information about a lemma"""

    name: str
    file_path: str
    line_number: int | None
    documentation: str
    signature: str
    requires_clauses: list[str]
    ensures_clauses: list[str]
    symbol_id: str
    source: str = "project"  # "project" or "vstd" or other source

    def to_searchable_text(self, normalize: bool = False) -> str:
        """
        Convert to natural language for search.

        Args:
            normalize: If True, apply mathematical normalization to improve matching
        """
        parts = [
            f"Name: {self.name}",
            f"Documentation: {self.documentation}",
            f"Signature: {self.signature}",
        ]

        if self.requires_clauses:
            # Convert requires to natural language
            reqs = " AND ".join(self.requires_clauses)
            parts.append(f"Preconditions: {reqs}")

        if self.ensures_clauses:
            # Convert ensures to natural language
            enss = " AND ".join(self.ensures_clauses)
            parts.append(f"Postconditions: {enss}")

        text = " ".join(parts)

        # Optionally normalize for better matching
        if normalize:
            # Apply operator normalization (but not variable renaming for lemmas)
            # Use QueryNormalizer to avoid code duplication
            from .normalization import QueryNormalizer
            normalizer = QueryNormalizer()
            text = normalizer.normalize_operators_only(text)

        return text

    def to_display(self) -> str:
        """Format for user display"""
        source_icon = "📦" if self.source == "vstd" else "📁"
        source_label = f" ({self.source})" if self.source != "project" else ""
        lines = [
            f"📋 {self.name}{source_label}",
            f"   {source_icon} {self.file_path}"
            + (f":{self.line_number}" if self.line_number else ""),
        ]

        if self.documentation:
            lines.append(f"   💬 {self.documentation}")

        lines.append(f"   ✍️  {self.signature}")

        if self.requires_clauses:
            lines.append("   ✓ requires:")
            for req in self.requires_clauses:
                lines.append(f"      • {req.strip()}")

        if self.ensures_clauses:
            lines.append("   ✓ ensures:")
            for ens in self.ensures_clauses:
                lines.append(f"      • {ens.strip()}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
