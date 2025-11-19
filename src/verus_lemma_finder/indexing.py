"""
Lemma indexing from SCIP data.
"""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .config import Config, get_config
from .extraction import SpecExtractor
from .models import LemmaInfo
from .utils import EMBEDDINGS_AVAILABLE, get_sentence_transformer_model

# Type checking imports (for static analysis only)
if TYPE_CHECKING:
    import numpy as np


class LemmaIndexer:
    """Build searchable index from SCIP data"""

    def __init__(
        self,
        scip_file: Path,
        repo_root: Path,
        use_embeddings: bool = False,
        source: str = "project",
        path_filter: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        self.scip_file = scip_file
        self.repo_root = repo_root
        self.config = config if config is not None else get_config()
        self.spec_extractor = SpecExtractor(repo_root, config=self.config)
        self.lemmas: List[LemmaInfo] = []
        self.use_embeddings = use_embeddings
        self.embeddings = None
        self.model = None
        self.source = source  # Tag for where lemmas come from
        self.path_filter = (
            path_filter  # Optional path prefix to filter (e.g., "source/vstd")
        )

        # Cache for symbol -> line number mapping from SCIP occurrences
        self.symbol_line_map: Dict[str, int] = {}

        if use_embeddings:
            if not EMBEDDINGS_AVAILABLE:
                print("⚠️  Warning: sentence-transformers not available. Install with:")
                print("    uv pip install sentence-transformers")
                print("    Continuing without embeddings.")
                self.use_embeddings = False
            else:
                # Use cached model to avoid reloading
                self.model = get_sentence_transformer_model(
                    self.config.indexing.embedding_model
                )

    def _extract_line_numbers_from_occurrences(
        self, occurrences: List[Dict]
    ) -> Dict[str, int]:
        """
        Extract line numbers from SCIP occurrences.

        Returns a mapping of symbol_id -> line_number (1-indexed)
        Filters for definitions only (symbol_roles == 1)
        """
        line_map = {}
        for occ in occurrences:
            symbol_id = occ.get("symbol", "")
            symbol_roles = occ.get("symbol_roles", 0)
            range_data = occ.get("range", [])

            # symbol_roles == 1 means this is a definition (not a reference)
            if symbol_roles == self.config.indexing.scip_definition_role and range_data:
                # range[0] is the line number (0-indexed), convert to 1-indexed
                line_number = range_data[0] + 1
                line_map[symbol_id] = line_number

        return line_map

    def _should_index_document(self, path: str) -> bool:
        """
        Determine if a document should be indexed based on path filtering.

        Args:
            path: Relative path of the document

        Returns:
            True if document should be indexed, False otherwise
        """
        # Apply path filter if specified (e.g., only index vstd files)
        if self.path_filter:
            return path.startswith(self.path_filter)

        # Focus on lemma files and specs (if no path filter, use default filtering)
        return any(keyword in path for keyword in self.config.indexing.lemma_file_keywords)

    def _should_index_symbol(self, symbol: Dict[str, Any], name: str) -> bool:
        """
        Determine if a symbol should be indexed as a lemma.

        Args:
            symbol: Symbol dictionary from SCIP data
            name: Display name of the symbol

        Returns:
            True if symbol should be indexed, False otherwise
        """
        # Filter for functions only
        if symbol.get("kind") != self.config.indexing.scip_function_kind:
            return False

        # Include lemma_, axiom_, proof functions, and spec_ functions
        if any(prefix in name for prefix in self.config.indexing.lemma_function_prefixes):
            return True

        # Also include proof fns even without prefix
        sig = symbol.get("signature_documentation", {})
        return "proof" in sig.get("text", "")

    def _create_lemma_from_symbol(
        self, symbol: Dict[str, Any], doc_line_map: Dict[str, int], default_path: str
    ) -> Tuple[LemmaInfo, bool]:
        """
        Create a LemmaInfo object from a SCIP symbol.

        Args:
            symbol: Symbol dictionary from SCIP data
            doc_line_map: Mapping of symbol_id to line numbers
            default_path: Default file path if not in signature

        Returns:
            Tuple of (LemmaInfo object, whether line number came from SCIP)
        """
        name = symbol.get("display_name", "")
        symbol_id = symbol.get("symbol", "")
        documentation = " ".join(symbol.get("documentation", []))

        sig_doc = symbol.get("signature_documentation", {})
        signature = sig_doc.get("text", "")
        file_path = sig_doc.get("relative_path", default_path)

        # Get line number from SCIP occurrences (faster and more reliable!)
        line_num = doc_line_map.get(symbol_id)
        line_from_scip = line_num is not None

        # Extract requires/ensures from source (not available in SCIP)
        requires, ensures, parsed_line_num = (
            self.spec_extractor.extract_specs_for_function(file_path, name)
        )

        # Use SCIP line number if available, fallback to parsed
        if line_num is None:
            line_num = parsed_line_num

        lemma = LemmaInfo(
            name=name,
            file_path=file_path,
            line_number=line_num,
            documentation=documentation,
            signature=signature,
            requires_clauses=requires,
            ensures_clauses=ensures,
            symbol_id=symbol_id,
            source=self.source,
        )

        return lemma, line_from_scip

    def _compute_embeddings_if_needed(self) -> None:
        """Compute embeddings for all indexed lemmas if embeddings are enabled."""
        if not (self.use_embeddings and self.model):
            return

        print("Computing embeddings...")
        start_time = time.time()
        # Use normalized text for better matching across different phrasings
        texts = [lemma.to_searchable_text(normalize=True) for lemma in self.lemmas]
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        elapsed = time.time() - start_time
        print(f"✓ Computed embeddings in {elapsed:.1f}s")

    def _print_indexing_statistics(
        self, lemma_count: int, line_nums_from_scip: int, line_nums_from_parsing: int
    ) -> None:
        """Print statistics about the indexing process."""
        print(f"Indexed {lemma_count} lemmas/specs")
        if lemma_count > 0:
            scip_percentage = 100 * line_nums_from_scip / lemma_count
            parsing_percentage = 100 * line_nums_from_parsing / lemma_count
            print(f"  Line numbers from SCIP: {line_nums_from_scip} ({scip_percentage:.1f}%)")
            print(
                f"  Line numbers from parsing: {line_nums_from_parsing} ({parsing_percentage:.1f}%)"
            )

    def build_index(self) -> List[LemmaInfo]:
        """
        Extract all lemmas from SCIP data.

        Processes SCIP documents and symbols to build a searchable index of lemmas.
        Optionally computes embeddings for semantic search.

        Returns:
            List of extracted LemmaInfo objects
        """
        print(f"Loading SCIP data from {self.scip_file}...")

        with open(self.scip_file) as f:
            scip_data = json.load(f)

        documents = scip_data.get("documents", [])
        print(f"Found {len(documents)} documents")

        lemma_count = 0
        line_nums_from_scip = 0
        line_nums_from_parsing = 0

        for doc in documents:
            path = doc.get("relative_path", "")

            # Skip documents that don't match our filtering criteria
            if not self._should_index_document(path):
                continue

            # Extract line numbers from occurrences for this document
            occurrences = doc.get("occurrences", [])
            doc_line_map = self._extract_line_numbers_from_occurrences(occurrences)

            # Process each symbol in the document
            for symbol in doc.get("symbols", []):
                name = symbol.get("display_name", "")

                # Skip symbols that aren't lemmas or spec functions
                if not self._should_index_symbol(symbol, name):
                    continue

                # Create lemma from symbol
                lemma, line_from_scip = self._create_lemma_from_symbol(
                    symbol, doc_line_map, path
                )

                # Track statistics
                if line_from_scip:
                    line_nums_from_scip += 1
                else:
                    line_nums_from_parsing += 1

                self.lemmas.append(lemma)
                lemma_count += 1

        # Print indexing statistics
        self._print_indexing_statistics(lemma_count, line_nums_from_scip, line_nums_from_parsing)

        # Compute embeddings if needed
        self._compute_embeddings_if_needed()

        return self.lemmas

    def save_index(self, output_file: Path) -> None:
        """Save index to JSON"""
        index_data = {
            "version": "1.0",
            "repo_root": str(self.repo_root),
            "lemmas": [lemma.to_dict() for lemma in self.lemmas],
            "has_embeddings": self.embeddings is not None,
        }

        with open(output_file, "w") as f:
            json.dump(index_data, f, indent=2)

        print(f"Saved index to {output_file}")

        # Save embeddings separately (binary format for efficiency)
        if self.embeddings is not None:
            embeddings_file = output_file.with_suffix(".embeddings.npy")
            np.save(embeddings_file, self.embeddings)
            print(f"Saved embeddings to {embeddings_file}")
            print(f"  Shape: {self.embeddings.shape}")
            print(f"  Size: {embeddings_file.stat().st_size / 1024 / 1024:.1f} MB")


def merge_indexes(
    base_index_file: Path,
    new_lemmas: List[LemmaInfo],
    output_file: Path,
    embeddings_array: Optional[Any] = None,
) -> None:
    """Merge new lemmas into an existing index"""
    # Load base index
    with open(base_index_file) as f:
        base_data = json.load(f)

    base_lemmas = [
        LemmaInfo(**lemma_dict) for lemma_dict in base_data.get("lemmas", [])
    ]

    # Load base embeddings if they exist
    base_embeddings: Optional[Any] = None
    embeddings_file = base_index_file.with_suffix(".embeddings.npy")
    if embeddings_file.exists() and EMBEDDINGS_AVAILABLE:
        base_embeddings = np.load(embeddings_file)

    # Merge lemmas
    all_lemmas = base_lemmas + new_lemmas
    print(f"  Base lemmas: {len(base_lemmas)}")
    print(f"  New lemmas: {len(new_lemmas)}")
    print(f"  Total: {len(all_lemmas)}")

    # Merge embeddings if available
    merged_embeddings: Optional[Any] = None
    if base_embeddings is not None and embeddings_array is not None:
        merged_embeddings = np.vstack([base_embeddings, embeddings_array])
        print(f"  Merged embeddings: {merged_embeddings.shape}")

    # Save merged index
    index_data = {
        "version": "1.0",
        "repo_root": base_data.get("repo_root", ""),
        "lemmas": [lemma.to_dict() for lemma in all_lemmas],
        "has_embeddings": merged_embeddings is not None,
    }

    with open(output_file, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"✓ Saved merged index to {output_file}")

    # Save merged embeddings
    if merged_embeddings is not None:
        merged_embeddings_file = output_file.with_suffix(".embeddings.npy")
        np.save(merged_embeddings_file, merged_embeddings)
        print(f"✓ Saved merged embeddings to {merged_embeddings_file}")
