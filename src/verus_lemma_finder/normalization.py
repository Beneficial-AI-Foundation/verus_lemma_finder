"""
Query normalization for improving search matching.
"""

import re
from typing import List


class QueryNormalizer:
    """Normalize and generate variations of search queries"""

    def __init__(self) -> None:
        self.math_replacements = {
            r"\btimes\b": "*",
            r"\bmul\b": "*",
            r"\bmultiply\b": "*",
            r"\bdiv\b": "/",
            r"\bdivide\b": "/",
            # NOTE: Keep 'mod' and 'modulo' as-is for better semantic matching
            # The embedding model understands these words but not the '%' symbol
            r"\bmodulo\b": "mod",  # Normalize modulo to mod for consistency
            r"\bwhen\b": "if",  # Normalize "when" to "if" for variation generation
            r"\biff\b": "if and only if",
            r"\bleq\b": "<=",
            r"\bgeq\b": ">=",
            r"\bneq\b": "!=",
        }

    def normalize(self, query: str) -> str:
        """
        Normalize a query by applying mathematical operator normalization
        and variable name normalization.
        """
        result = self._normalize_operators(query)
        result = self._normalize_variables(result)
        return result

    def normalize_operators_only(self, text: str) -> str:
        """
        Normalize only mathematical operators and words (no variable renaming).

        This is useful for normalizing lemma text where we want to keep original
        variable names but standardize operator representations.

        Args:
            text: Text to normalize

        Returns:
            Text with normalized operators
        """
        return self._normalize_operators(text)

    def _normalize_operators(self, query: str) -> str:
        """Normalize mathematical operators and words (internal implementation)"""
        result = query
        for pattern, replacement in self.math_replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _normalize_variables(self, query: str) -> str:
        """
        Normalize variable names to generic placeholders.
        This helps match queries with different variable names.
        """
        # Find all single-letter variables used in mathematical context
        # Pattern: single letter followed by math operator or comparison
        var_pattern = r"\b([a-z])\b(?=\s*[*+\-/<>=]|\s+if\b|\s+then\b)"
        variables_found = re.findall(var_pattern, query, flags=re.IGNORECASE)

        if not variables_found:
            return query

        # Create consistent mapping (first var -> var1, second -> var2, etc)
        unique_vars: List[str] = []
        for v in variables_found:
            if v.lower() not in [u.lower() for u in unique_vars]:
                unique_vars.append(v.lower())

        # Sort variables alphabetically to ensure consistency
        unique_vars.sort()

        # Replace with generic names
        result = query
        for i, var in enumerate(unique_vars):
            # Use var1, var2, var3 as generic names
            generic_name = f"var{i + 1}"
            # Use word boundaries to avoid partial matches
            result = re.sub(rf"\b{var}\b", generic_name, result, flags=re.IGNORECASE)

        return result

    def generate_variations(self, query: str) -> List[str]:
        """
        Generate variations of a query to handle different phrasings.
        This helps match semantically equivalent but syntactically different queries.
        """
        variations = [query]

        # Variation 0: Add mod/% variants since documentation uses % but users type "mod"
        # Generate versions with both if either is present
        if "mod" in query.lower() and "%" not in query:
            variations.append(query.replace("mod", "%"))
        elif "%" in query and "mod" not in query.lower():
            variations.append(query.replace("%", "mod"))

        # Variation 1: Swap implication order
        # "if A then B" <-> "B if A"
        # Pattern: "if ... then ..."
        if_then_pattern = r"if\s+(.+?)\s+then\s+(.+?)$"
        match = re.search(if_then_pattern, query, flags=re.IGNORECASE)
        if match:
            condition = match.group(1).strip()
            conclusion = match.group(2).strip()
            # Create reverse order: "conclusion if condition"
            reverse = f"{conclusion} if {condition}"
            variations.append(reverse)

        # Also handle reverse: "B if A and C" -> "if A and C then B"
        # Use greedy match for condition to capture all "and" clauses
        backward_if_pattern = r"^(.+?)\s+if\s+(.+)$"
        match = re.search(backward_if_pattern, query, flags=re.IGNORECASE)
        if match and "then" not in query.lower():  # Only if not already in if-then form
            conclusion = match.group(1).strip()
            condition = match.group(2).strip()
            forward = f"if {condition} then {conclusion}"
            variations.append(forward)

            # Also try swapping condition parts (A and B -> B and A)
            if " and " in condition.lower():
                parts = re.split(r"\s+and\s+", condition, flags=re.IGNORECASE)
                if len(parts) == 2:
                    swapped_condition = f"{parts[1]} and {parts[0]}"
                    variations.append(f"{conclusion} if {swapped_condition}")
                    variations.append(f"if {swapped_condition} then {conclusion}")

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v not in seen:
                seen.add(v)
                unique_variations.append(v)

        return unique_variations
