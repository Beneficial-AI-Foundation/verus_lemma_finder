"""
Lemma search functionality with semantic and keyword search.
"""

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from .config import Config, get_config
from .models import LemmaInfo
from .normalization import QueryNormalizer
from .utils import EMBEDDINGS_AVAILABLE, get_sentence_transformer_model

# Type checking imports (for static analysis only)
if TYPE_CHECKING:
    import numpy as np


class LemmaSearcher:
    """Search for lemmas using various strategies"""

    def __init__(self, index_file: Path, use_embeddings: bool = True, config: Optional[Config] = None):
        self.index_file = index_file
        self.lemmas: List[LemmaInfo] = []
        self.embeddings = None
        self.model = None
        self.use_embeddings = use_embeddings
        self.normalizer = QueryNormalizer()
        self.config = config if config is not None else get_config()
        self.load_index()

    def load_index(self) -> None:
        """Load pre-built index"""
        with open(self.index_file) as f:
            data = json.load(f)

        for lemma_dict in data.get('lemmas', []):
            self.lemmas.append(LemmaInfo(**lemma_dict))

        print(f"Loaded {len(self.lemmas)} lemmas from index")

        # Try to load embeddings if available
        has_embeddings = data.get('has_embeddings', False)
        if has_embeddings and self.use_embeddings:
            embeddings_file = self.index_file.with_suffix('.embeddings.npy')
            if embeddings_file.exists():
                if not EMBEDDINGS_AVAILABLE:
                    print("⚠️  Embeddings available but sentence-transformers not installed")
                    print("   Falling back to keyword search")
                else:
                    self.embeddings = np.load(embeddings_file)
                    if self.embeddings is not None:
                        print(f"✓ Loaded embeddings: {self.embeddings.shape}")
                    # Load model for query encoding (cached at module level)
                    self.model = get_sentence_transformer_model(self.config.search.embedding_model)
            else:
                print("⚠️  Embeddings file not found, using keyword search")

    def keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[LemmaInfo, float]]:
        """Simple keyword-based search"""
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))

        results = []

        for lemma in self.lemmas:
            searchable = lemma.to_searchable_text().lower()
            searchable_terms = set(re.findall(r'\w+', searchable))

            # Calculate score based on term overlap
            overlap = len(query_terms & searchable_terms)

            # Bonus for matches in name
            name_lower = lemma.name.lower()
            name_matches = sum(1 for term in query_terms if term in name_lower)

            # Bonus for matches in documentation
            doc_lower = lemma.documentation.lower()
            doc_matches = sum(1 for term in query_terms if term in doc_lower)

            score = (overlap +
                    name_matches * self.config.search.name_match_boost +
                    doc_matches * self.config.search.doc_match_boost)

            if score > 0:
                results.append((lemma, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def semantic_search(self, query: str, top_k: int = 10) -> List[Tuple[LemmaInfo, float]]:
        """Semantic search using embeddings"""
        if self.embeddings is None or self.model is None:
            print("⚠️  Embeddings not available, falling back to keyword search")
            return self.keyword_search(query, top_k)

        # Encode query
        query_embedding = self.model.encode([query])[0]

        # Compute cosine similarities
        # Normalize embeddings for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)

        similarities = embeddings_norm @ query_norm

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((self.lemmas[idx], float(similarities[idx])))

        return results

    def hybrid_search(self, query: str, top_k: int = 10, keyword_weight: Optional[float] = None) -> List[Tuple[LemmaInfo, float]]:
        """Hybrid search combining keyword and semantic search"""
        if self.embeddings is None:
            return self.keyword_search(query, top_k)

        # Use config value if not provided
        if keyword_weight is None:
            keyword_weight = self.config.search.keyword_weight

        # Get results from both methods
        semantic_results = self.semantic_search(query, top_k * 2)
        keyword_results = self.keyword_search(query, top_k * 2)

        # Combine scores
        combined_scores = {}

        # Normalize semantic scores to [0, 1] range (they're already similarities)
        max_semantic = max((score for _, score in semantic_results), default=1.0)
        for lemma, score in semantic_results:
            lemma_key = lemma.name
            normalized_score = score / max_semantic if max_semantic > 0 else 0
            combined_scores[lemma_key] = {
                'lemma': lemma,
                'score': normalized_score * (1 - keyword_weight)
            }

        # Normalize keyword scores
        max_keyword = max((score for _, score in keyword_results), default=1.0)
        for lemma, score in keyword_results:
            lemma_key = lemma.name
            normalized_score = score / max_keyword if max_keyword > 0 else 0

            if lemma_key in combined_scores:
                combined_scores[lemma_key]['score'] += normalized_score * keyword_weight
            else:
                combined_scores[lemma_key] = {
                    'lemma': lemma,
                    'score': normalized_score * keyword_weight
                }

        # Sort by combined score
        results = [(v['lemma'], v['score']) for v in combined_scores.values()]
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def fuzzy_search(self, query: str, top_k: int = 10) -> List[Tuple[LemmaInfo, float]]:
        """
        Fuzzy search with mathematical awareness - uses best available method.

        This is the main search method that:
        1. Normalizes the query
        2. Generates variations
        3. Searches with all variations
        4. Combines results
        """
        # Normalize query: convert common math phrases
        normalized = self.normalizer.normalize(query)

        # Generate query variations to handle different phrasings
        query_variations = self.normalizer.generate_variations(normalized)

        # Use semantic search if available, otherwise keyword
        if self.embeddings is not None:
            # Search with all variations and combine results
            all_results = {}
            for variation in query_variations:
                results = self.hybrid_search(variation, top_k * 2)
                for lemma, score in results:
                    key = lemma.name
                    # Keep the best score across all variations
                    if key not in all_results or score > all_results[key][1]:
                        all_results[key] = (lemma, score)

            # Sort by score and return top-k
            combined = list(all_results.values())
            combined.sort(key=lambda x: x[1], reverse=True)
            return combined[:top_k]
        else:
            return self.keyword_search(normalized, top_k)

    # Alias for backward compatibility
    def search(self, query: str, top_k: int = 10) -> List[Tuple[LemmaInfo, float]]:
        """Alias for fuzzy_search"""
        return self.fuzzy_search(query, top_k)

