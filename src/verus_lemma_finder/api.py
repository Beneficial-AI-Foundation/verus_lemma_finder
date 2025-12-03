"""
Public API for verus_lemma_finder.

This module exposes simple functions that can be imported and used as a library.

Example usage:
    from verus_lemma_finder.api import get_similar_lemmas, load_searcher

    # Option 1: One-shot search (loads index each time)
    results = get_similar_lemmas(
        query="lemma about modulo bounds",
        index_path="data/curve25519-dalek_lemma_index.json",
        top_k=3
    )

    # Option 2: Reuse searcher for multiple queries (more efficient)
    searcher = load_searcher("data/curve25519-dalek_lemma_index.json")
    results1 = get_similar_lemmas("modulo bounds", searcher=searcher)
    results2 = get_similar_lemmas("multiplication overflow", searcher=searcher)

    # Option 3: Find lemmas similar to an existing lemma (by name)
    results = get_similar_to_lemma(
        lemma_name="lemma_mod_division_less_than_divisor",
        index_path="data/vstd_lemma_index.json",
        top_k=5
    )
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .search import LemmaSearcher


@dataclass
class SimilarLemma:
    """A similar lemma result with metadata."""
    name: str
    score: float
    file_path: str
    line_number: int | None
    signature: str
    source: str  # "project" or "vstd"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "file_path": self.file_path,
            "line_number": self.line_number,
            "signature": self.signature,
            "source": self.source,
        }


def load_searcher(index_path: str | Path, use_embeddings: bool = True) -> "LemmaSearcher":
    """
    Load a lemma searcher from an index file.
    
    Use this when you need to perform multiple searches - it's more efficient
    than calling get_similar_lemmas() repeatedly with just a path.
    
    Args:
        index_path: Path to the lemma index JSON file
        use_embeddings: Whether to use semantic embeddings (default: True)
    
    Returns:
        A LemmaSearcher instance that can be reused for multiple queries
    """
    from .search import LemmaSearcher
    return LemmaSearcher(Path(index_path), use_embeddings=use_embeddings)


def get_similar_lemmas(
    query: str,
    index_path: str | Path | None = None,
    searcher: "LemmaSearcher | None" = None,
    top_k: int = 3,
    exclude_self: bool = True,
    auto_detect_lemma: bool = True,
) -> list[SimilarLemma]:
    """
    Find lemmas similar to the given query.
    
    If the query matches an existing lemma name in the index and auto_detect_lemma
    is True, this will automatically use the lemma's full definition to find
    similar lemmas (equivalent to calling get_similar_to_lemma).
    
    Args:
        query: The lemma name, signature, or description to search for
        index_path: Path to the lemma index JSON file (required if searcher not provided)
        searcher: A pre-loaded LemmaSearcher instance (more efficient for multiple queries)
        top_k: Number of similar lemmas to return (default: 3)
        exclude_self: If True, exclude exact name matches from results (default: True)
        auto_detect_lemma: If True and query matches a lemma name, use its definition
                          for the search (default: True)
    
    Returns:
        List of SimilarLemma objects, sorted by similarity score (highest first)
    
    Example:
        # Search by natural language query
        results = get_similar_lemmas(
            query="remainder is less than divisor",
            index_path="data/vstd_lemma_index.json",
            top_k=3
        )
        
        # Search by lemma name (auto-detected, uses lemma's definition)
        results = get_similar_lemmas(
            query="lemma_mod_division_less_than_divisor",
            index_path="data/vstd_lemma_index.json",
            top_k=3
        )
        
        for lemma in results:
            print(f"{lemma.name}: {lemma.score:.2f}")
    
    Raises:
        ValueError: If neither index_path nor searcher is provided
    """
    # Get or create searcher
    if searcher is None:
        if index_path is None:
            raise ValueError("Either index_path or searcher must be provided")
        searcher = load_searcher(index_path)
    
    # Check if query is a lemma name (auto-detect)
    if auto_detect_lemma:
        source_lemma = searcher.get_lemma_by_name(query)
        if source_lemma is not None:
            # Query is a lemma name - use find_similar_lemmas
            results = searcher.find_similar_lemmas(query, top_k=top_k)
            
            # Convert to SimilarLemma objects
            return [
                SimilarLemma(
                    name=lemma.name,
                    score=score,
                    file_path=lemma.file_path,
                    line_number=lemma.line_number,
                    signature=lemma.signature,
                    source=lemma.source,
                )
                for lemma, score in results
            ]
    
    # Query is not a lemma name (or auto-detect disabled) - do regular search
    search_k = top_k + 1 if exclude_self else top_k
    results = searcher.search(query, top_k=search_k)
    
    # Convert to SimilarLemma objects
    similar_lemmas = []
    query_name = query.split()[0] if query else ""  # First word might be lemma name
    
    for lemma, score in results:
        # Optionally skip exact name matches
        if exclude_self and lemma.name == query_name:
            continue
        
        similar_lemmas.append(SimilarLemma(
            name=lemma.name,
            score=score,
            file_path=lemma.file_path,
            line_number=lemma.line_number,
            signature=lemma.signature,
            source=lemma.source,
        ))
        
        if len(similar_lemmas) >= top_k:
            break
    
    return similar_lemmas


def get_similar_lemmas_dict(
    query: str,
    index_path: str | Path | None = None,
    searcher: "LemmaSearcher | None" = None,
    top_k: int = 3,
    exclude_self: bool = True,
) -> list[dict]:
    """
    Same as get_similar_lemmas but returns dictionaries instead of dataclass objects.
    
    Useful for JSON serialization or when you don't want to import the SimilarLemma class.
    
    Returns:
        List of dictionaries with keys: name, score, file_path, line_number, signature, source
    """
    results = get_similar_lemmas(
        query=query,
        index_path=index_path,
        searcher=searcher,
        top_k=top_k,
        exclude_self=exclude_self,
    )
    return [r.to_dict() for r in results]


def get_similar_to_lemma(
    lemma_name: str,
    index_path: str | Path | None = None,
    searcher: "LemmaSearcher | None" = None,
    top_k: int = 3,
) -> list[SimilarLemma]:
    """
    Find lemmas similar to an existing lemma (by name).
    
    This looks up the lemma by its exact name in the index, retrieves its full
    definition (signature, documentation, requires/ensures clauses), and finds
    other lemmas with similar semantics.
    
    Args:
        lemma_name: The exact name of the lemma to find similar lemmas for
        index_path: Path to the lemma index JSON file (required if searcher not provided)
        searcher: A pre-loaded LemmaSearcher instance (more efficient for multiple queries)
        top_k: Number of similar lemmas to return (default: 3)
    
    Returns:
        List of SimilarLemma objects, sorted by similarity score (highest first).
        Returns empty list if the lemma is not found in the index.
    
    Example:
        # Find lemmas similar to a specific lemma
        results = get_similar_to_lemma(
            lemma_name="lemma_mod_division_less_than_divisor",
            index_path="data/vstd_lemma_index.json",
            top_k=5
        )
        for lemma in results:
            print(f"{lemma.name}: {lemma.score:.2f}")
    
    Raises:
        ValueError: If neither index_path nor searcher is provided
    """
    # Get or create searcher
    if searcher is None:
        if index_path is None:
            raise ValueError("Either index_path or searcher must be provided")
        searcher = load_searcher(index_path)
    
    # Use the searcher's find_similar_lemmas method
    results = searcher.find_similar_lemmas(lemma_name, top_k=top_k)
    
    # Convert to SimilarLemma objects
    similar_lemmas = []
    for lemma, score in results:
        similar_lemmas.append(SimilarLemma(
            name=lemma.name,
            score=score,
            file_path=lemma.file_path,
            line_number=lemma.line_number,
            signature=lemma.signature,
            source=lemma.source,
        ))
    
    return similar_lemmas


def get_similar_to_lemma_dict(
    lemma_name: str,
    index_path: str | Path | None = None,
    searcher: "LemmaSearcher | None" = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Same as get_similar_to_lemma but returns dictionaries instead of dataclass objects.
    
    Useful for JSON serialization or when you don't want to import the SimilarLemma class.
    
    Returns:
        List of dictionaries with keys: name, score, file_path, line_number, signature, source
    """
    results = get_similar_to_lemma(
        lemma_name=lemma_name,
        index_path=index_path,
        searcher=searcher,
        top_k=top_k,
    )
    return [r.to_dict() for r in results]

