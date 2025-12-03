"""
Command-line interface for the lemma search tool.
"""

import argparse
import json
import sys
from pathlib import Path

from .duplicates import DuplicateDetector, format_duplicate_report
from .indexing import LemmaIndexer, fill_empty_specs_from_reference, merge_indexes
from .models import LemmaInfo
from .scip_utils import clone_verus_repo, generate_scip_json
from .search import LemmaSearcher


def cmd_setup_vstd(args: argparse.Namespace) -> int:
    """Setup vstd by cloning Verus repo. Returns exit code (0 for success, non-zero for failure)."""
    target_dir = Path(args.target_dir) if args.target_dir else Path("./verus")

    print("=" * 70)
    print("🔧 Setting up vstd")
    print("=" * 70)
    print()

    if not clone_verus_repo(target_dir):
        print("\n❌ Failed to setup vstd")
        return 1

    vstd_path = target_dir / "source" / "vstd"
    if not vstd_path.exists():
        print(f"❌ Error: vstd directory not found at {vstd_path}")
        return 1

    print()
    print("=" * 70)
    print("✅ vstd setup complete!")
    print("=" * 70)
    print(f"\nvstd location: {vstd_path}")
    print("\nNext steps:")
    print("  1. Generate SCIP for Verus:")
    print(f"     uv run python -m verus_lemma_finder generate-scip {target_dir}")
    print("  2. Add vstd lemmas to your index:")
    print(
        f"     uv run python -m verus_lemma_finder add-vstd {target_dir}/<verus_scip>.json lemma_index.json"
    )
    return 0


def _validate_vstd_input_files(verus_scip: Path, base_index: Path, verus_root: Path) -> int | None:
    """
    Validate that required input files exist for vstd indexing.

    Args:
        verus_scip: Path to Verus SCIP file
        base_index: Path to base index file
        verus_root: Path to Verus repository root

    Returns:
        Error code (non-zero) if validation fails, None if validation passes
    """
    if not verus_scip.exists():
        print(f"❌ Error: Verus SCIP file not found: {verus_scip}")
        print("\nGenerate it with:")
        print(f"  uv run python -m verus_lemma_finder generate-scip {verus_root}")
        return 1

    if not base_index.exists():
        print(f"❌ Error: Base index not found: {base_index}")
        print("\nCreate it first with:")
        print("  uv run python -m verus_lemma_finder index <your_project_scip>.json")
        return 1

    return None


def _check_embeddings_compatibility(base_index: Path) -> tuple[bool, bool]:
    """
    Check if base index uses embeddings and if embeddings are available.

    Args:
        base_index: Path to base index file

    Returns:
        Tuple of (use_embeddings, embeddings_available)
    """
    import json

    # Check if base index has embeddings
    with open(base_index) as f:
        base_data = json.load(f)
    use_embeddings = base_data.get("has_embeddings", False)

    # Check if embeddings libraries are available
    try:
        import numpy  # noqa: F401
        import sentence_transformers  # noqa: F401

        embeddings_available = True
    except ImportError:
        embeddings_available = False

    # Warn if base index has embeddings but they're not available
    if use_embeddings and not embeddings_available:
        print("⚠️  Warning: Base index has embeddings but sentence-transformers not available")
        print("   New vstd lemmas will be added without embeddings")
        use_embeddings = False

    return use_embeddings, embeddings_available


def cmd_add_vstd(args: argparse.Namespace) -> int:
    """Add vstd lemmas to existing index. Returns exit code (0 for success, non-zero for failure)."""
    verus_scip = Path(args.verus_scip_file)
    base_index = Path(args.base_index_file)
    output = Path(args.output) if args.output else base_index
    verus_root = Path(args.verus_root) if args.verus_root else verus_scip.parent

    print("=" * 70)
    print("📦 Adding vstd lemmas to index")
    print("=" * 70)
    print()

    # Validate input files
    validation_error = _validate_vstd_input_files(verus_scip, base_index, verus_root)
    if validation_error is not None:
        return validation_error

    # Check embeddings compatibility
    use_embeddings, _ = _check_embeddings_compatibility(base_index)

    print(f"Indexing vstd from: {verus_scip}")
    print("Filtering to: source/vstd")
    print(f"Using embeddings: {use_embeddings}")
    print()

    # Index vstd lemmas only
    indexer = LemmaIndexer(
        verus_scip,
        verus_root,
        use_embeddings=use_embeddings,
        source="vstd",
        path_filter="source/vstd",
    )

    vstd_lemmas = indexer.build_index()

    if not vstd_lemmas:
        print("⚠️  No vstd lemmas found")
        return 1

    print()
    print("Merging with base index...")
    merge_indexes(base_index, vstd_lemmas, output, indexer.embeddings)

    print()
    print("=" * 70)
    print("✅ vstd lemmas added successfully!")
    print("=" * 70)
    print(f"\nUpdated index: {output}")
    print("\nYou can now search both project and vstd lemmas:")
    print(f'  uv run python -m verus_lemma_finder search "your query" {output}')
    return 0


def cmd_fill_specs(args: argparse.Namespace) -> int:
    """Fill empty specs from a reference index. Returns exit code (0 for success, non-zero for failure)."""
    import numpy as np

    index_file = Path(args.index_file)
    reference_file = Path(args.reference_index)
    output_file = Path(args.output) if args.output else index_file

    if not index_file.exists():
        print(f"❌ Error: Index file not found: {index_file}")
        return 1

    if not reference_file.exists():
        print(f"❌ Error: Reference index not found: {reference_file}")
        return 1

    print("=" * 70)
    print("📚 Filling Empty Specs from Reference Index")
    print("=" * 70)
    print()
    print(f"   Source index: {index_file}")
    print(f"   Reference:    {reference_file}")
    print(f"   Output:       {output_file}")
    print()

    # Load source index
    with open(index_file) as f:
        index_data = json.load(f)

    lemmas = [LemmaInfo(**d) for d in index_data.get("lemmas", [])]
    print(f"   Loaded {len(lemmas)} lemmas from source")

    # Count lemmas without specs before
    before_count = len(
        [lem for lem in lemmas if not lem.requires_clauses and not lem.ensures_clauses]
    )
    print(f"   Lemmas without specs: {before_count}")
    print()

    # Fill from reference
    updated_lemmas, filled_count = fill_empty_specs_from_reference(lemmas, reference_file)
    print(f"   ✅ Filled {filled_count} lemmas from reference")

    # Update index
    index_data["lemmas"] = [
        {k: v for k, v in lem.__dict__.items() if v is not None} for lem in updated_lemmas
    ]

    # Save updated index
    with open(output_file, "w") as f:
        json.dump(index_data, f, indent=2)
    print(f"\n💾 Saved to: {output_file}")

    # Recompute embeddings if they exist
    embeddings_file = index_file.with_suffix(".embeddings.npy")
    if embeddings_file.exists() and filled_count > 0:
        print("\n🔄 Recomputing embeddings...")
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")

            texts = []
            for lemma in updated_lemmas:
                text_parts = [lemma.name]
                if lemma.documentation:
                    text_parts.append(lemma.documentation)
                if lemma.signature:
                    text_parts.append(lemma.signature)
                if lemma.requires_clauses:
                    text_parts.extend(lemma.requires_clauses)
                if lemma.ensures_clauses:
                    text_parts.extend(lemma.ensures_clauses)
                texts.append(" ".join(text_parts))

            embeddings = model.encode(texts, show_progress_bar=True)
            output_embeddings_file = output_file.with_suffix(".embeddings.npy")
            np.save(output_embeddings_file, embeddings)
            print(f"💾 Saved embeddings to: {output_embeddings_file}")
        except ImportError:
            print("⚠️  sentence-transformers not installed, skipping embeddings")

    after_count = len(
        [lem for lem in updated_lemmas if not lem.requires_clauses and not lem.ensures_clauses]
    )
    print()
    print("=" * 70)
    print("✅ Done!")
    print("=" * 70)
    print(f"\n   Before: {before_count} lemmas without specs")
    print(f"   After:  {after_count} lemmas without specs")
    print(f"   Improvement: {before_count - after_count} lemmas filled")

    return 0


def cmd_generate_scip(args: argparse.Namespace) -> int:
    """Generate SCIP JSON file. Returns exit code (0 for success, non-zero for failure)."""
    project_dir = Path(args.project_dir)

    if not project_dir.exists():
        print(f"❌ Error: Project directory not found: {project_dir}")
        return 1

    if not project_dir.is_dir():
        print(f"❌ Error: Not a directory: {project_dir}")
        return 1

    # Determine output file name
    if args.output:
        output_file = Path(args.output)
    else:
        # Use project directory name
        project_name = project_dir.resolve().name
        output_file = project_dir / f"{project_name}_scip.json"

    print(f"🎯 Project directory: {project_dir}")
    print(f"🎯 Output file: {output_file}")
    print()

    success = generate_scip_json(project_dir, output_file)

    if success:
        print()
        print("=" * 70)
        print("✅ SCIP JSON generation complete!")
        print("=" * 70)
        print("\nNext step: Build lemma index with:")
        print(f"  uv run python -m verus_lemma_finder index {output_file}")
        return 0
    else:
        print()
        print("=" * 70)
        print("❌ SCIP JSON generation failed")
        print("=" * 70)
        return 1


def cmd_index(args: argparse.Namespace) -> int:
    """Build lemma index. Returns exit code (0 for success, non-zero for failure)."""
    scip_file = Path(args.scip_file)
    repo_root = Path(args.repo_root) if args.repo_root else scip_file.parent
    output = Path(args.output) if args.output else Path("lemma_index.json")

    # Check if we should generate SCIP first
    if hasattr(args, "generate_scip") and args.generate_scip:
        if not scip_file.exists():
            print("📋 SCIP file not found, generating it first...")
            print()
            success = generate_scip_json(repo_root, scip_file)
            if not success:
                print("\n❌ Failed to generate SCIP file")
                return 1
            print()
        else:
            print(f"ℹ️  SCIP file already exists: {scip_file}")

    if not scip_file.exists():
        print(f"❌ Error: SCIP file not found: {scip_file}")
        print("\nGenerate it with:")
        print(f"  uv run python -m verus_lemma_finder generate-scip {repo_root}")
        print("\nOr manually:")
        print(f"  cd {repo_root}")
        print("  verus-analyzer scip .")
        print(f"  scip print --json index.scip > {scip_file.name}")
        return 1

    use_embeddings = args.embeddings if hasattr(args, "embeddings") else False
    no_fill = args.no_fill if hasattr(args, "no_fill") else False
    path_filter = args.path_filter if hasattr(args, "path_filter") else None

    # Determine fill_from: explicit arg > default vstd > None
    fill_from = None
    if not no_fill:
        if hasattr(args, "fill_from") and args.fill_from:
            fill_from = Path(args.fill_from)
        else:
            # Default: try to find vstd index relative to package or common locations
            default_vstd_paths = [
                Path(__file__).parent.parent.parent
                / "data"
                / "vstd_lemma_index.json",  # package/../data/
                Path("data/vstd_lemma_index.json"),  # relative to cwd
            ]
            for vstd_path in default_vstd_paths:
                if vstd_path.exists():
                    fill_from = vstd_path
                    break

    try:
        indexer = LemmaIndexer(
            scip_file, repo_root, use_embeddings=use_embeddings, path_filter=path_filter
        )
        indexer.build_index()

        # Fill empty specs from reference index (vstd by default)
        if fill_from:
            if not fill_from.exists():
                print(f"⚠️  Warning: Reference index not found: {fill_from}")
            else:
                print(f"\n📚 Filling empty specs from: {fill_from}")
                indexer.lemmas, filled_count = fill_empty_specs_from_reference(
                    indexer.lemmas, fill_from
                )
                print(f"   Filled {filled_count} lemmas from reference")

                # Recompute embeddings if we filled any specs
                if filled_count > 0 and use_embeddings:
                    print("   Recomputing embeddings...")
                    indexer._compute_embeddings_if_needed()

        indexer.save_index(output)
        return 0
    except Exception as e:
        print(f"❌ Error building index: {e}")
        return 1


def cmd_search(args: argparse.Namespace) -> int:
    """Search for lemmas. Returns exit code (0 for success, non-zero for failure)."""
    index_file = Path(args.index_file)
    query = args.query

    if not index_file.exists():
        print(f"❌ Error: Index file not found: {index_file}")
        return 1

    try:
        searcher = LemmaSearcher(index_file)
        results = searcher.fuzzy_search(query, top_k=args.top_k)

        if not results:
            print("No results found.")
            return 0

        print(f"\n🔍 Found {len(results)} results for: '{query}'\n")
        print("=" * 80)

        for i, (lemma, score) in enumerate(results, 1):
            print(f"\n[{i}] Score: {score:.1f}")
            print(lemma.to_display())
            print("-" * 80)

        return 0
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return 1


def cmd_similar(args: argparse.Namespace) -> int:
    """Find lemmas similar to a given lemma (by name). Returns exit code (0 for success, non-zero for failure)."""
    index_file = Path(args.index_file)
    lemma_name = args.lemma_name

    if not index_file.exists():
        print(f"❌ Error: Index file not found: {index_file}")
        return 1

    try:
        searcher = LemmaSearcher(index_file)

        # Look up the source lemma
        source_lemma = searcher.get_lemma_by_name(lemma_name)
        if source_lemma is None:
            print(f"❌ Error: Lemma '{lemma_name}' not found in index")
            print("\nTip: Use 'search' command to find lemmas by query:")
            print(f'  uv run python -m verus_lemma_finder search "{lemma_name}" {index_file}')
            return 1

        # Show source lemma info
        print(f"\n📋 Source lemma: {source_lemma.name}")
        print(
            f"   📦 {source_lemma.file_path}"
            + (f":{source_lemma.line_number}" if source_lemma.line_number else "")
        )
        if source_lemma.documentation:
            print(
                f"   💬 {source_lemma.documentation[:100]}{'...' if len(source_lemma.documentation) > 100 else ''}"
            )
        print()

        # Find similar lemmas
        results = searcher.find_similar_lemmas(lemma_name, top_k=args.top_k)

        if not results:
            print("No similar lemmas found.")
            return 0

        print(f"🔍 Found {len(results)} similar lemmas:\n")
        print("=" * 80)

        for i, (lemma, score) in enumerate(results, 1):
            print(f"\n[{i}] Score: {score:.3f}")
            print(lemma.to_display())
            print("-" * 80)

        return 0
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return 1


def cmd_detect_duplicates(args: argparse.Namespace) -> int:
    """Detect duplicate and redundant lemmas. Returns exit code."""
    import json

    index_file = Path(args.index_file)
    threshold = args.threshold
    output_file = Path(args.output) if args.output else None
    include_similar = args.similar
    similar_threshold = args.similar_threshold

    if not index_file.exists():
        print(f"❌ Error: Index file not found: {index_file}")
        return 1

    print("=" * 70)
    print("🔍 Detecting Duplicate Lemmas")
    print("=" * 70)
    print(f"\n   Index: {index_file}")
    print(f"   Similarity threshold: {threshold}")
    if include_similar:
        print(f"   Similar pattern threshold: {similar_threshold}")
    print()

    try:
        detector = DuplicateDetector(index_file, similarity_threshold=threshold)
    except Exception as e:
        print(f"❌ Error loading index: {e}")
        return 1
    print(f"   Analyzing {len(detector.searcher.lemmas)} lemmas...")
    print()

    # Detect structural duplicates (EXACT and SUBSUMES)
    duplicates = detector.detect(top_k_per_lemma=10)

    # Optionally detect similar patterns
    if include_similar:
        similar_pairs = detector.detect_similar_patterns(
            similarity_threshold=similar_threshold, top_k_per_lemma=10
        )
        duplicates.extend(similar_pairs)

    if not duplicates:
        print("✅ No duplicates found!")
        return 0

    # Print report
    report = format_duplicate_report(duplicates)
    print(report)

    # Save JSON output if requested
    if output_file:
        output_data = {
            "threshold": threshold,
            "similar_threshold": similar_threshold if include_similar else None,
            "total": len(duplicates),
            "duplicates": [d.to_dict() for d in duplicates],
        }
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\n💾 Saved JSON report to: {output_file}")

    return 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive search mode. Returns exit code (0 for success, non-zero for failure)."""
    index_file = Path(args.index_file)

    if not index_file.exists():
        print(f"❌ Error: Index file not found: {index_file}")
        return 1

    try:
        searcher = LemmaSearcher(index_file)
    except Exception as e:
        print(f"❌ Error loading index: {e}")
        return 1

    print("🔍 Lemma Search - Interactive Mode")
    print("Type your query (or 'quit' to exit)\n")

    while True:
        try:
            query = input("Search> ").strip()

            if query.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not query:
                continue

            results = searcher.fuzzy_search(query, top_k=5)

            if not results:
                print("❌ No results found.\n")
                continue

            print(f"\n✅ Found {len(results)} results:\n")

            for i, (lemma, score) in enumerate(results, 1):
                print(f"[{i}] {lemma.name} (score: {score:.1f})")
                print(f"    {lemma.file_path}:{lemma.line_number}")
                if lemma.documentation:
                    print(f"    {lemma.documentation}")
                print()

            # Ask if user wants details
            choice = input("Enter number for details (or press Enter to continue): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    print("\n" + "=" * 80)
                    print(results[idx][0].to_display())
                    print("=" * 80 + "\n")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

    return 0


def cmd_enrich_graph(args: argparse.Namespace) -> int:
    """
    Enrich a call graph JSON with similar lemmas for each node.

    Returns exit code (0 for success, non-zero for failure).
    """
    import json

    graph_file = Path(args.graph_file)
    index_file = Path(args.index_file)
    output_file = Path(args.output) if args.output else graph_file
    top_k = args.top_k

    print("=" * 70)
    print("🔗 Enriching call graph with similar lemmas")
    print("=" * 70)
    print()

    # Validate input files
    if not graph_file.exists():
        print(f"❌ Error: Graph file not found: {graph_file}")
        return 1

    if not index_file.exists():
        print(f"❌ Error: Lemma index file not found: {index_file}")
        return 1

    # Load the graph
    print(f"📂 Loading graph from: {graph_file}")
    try:
        with open(graph_file) as f:
            graph = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing graph JSON: {e}")
        return 1

    nodes = graph.get("nodes", [])
    print(f"   Found {len(nodes)} nodes")

    # Load the lemma searcher
    print(f"📂 Loading lemma index from: {index_file}")
    try:
        searcher = LemmaSearcher(index_file, use_embeddings=True)
    except Exception as e:
        print(f"❌ Error loading lemma index: {e}")
        return 1

    print()
    print(f"🔍 Finding top {top_k} similar lemmas for each node...")
    print()

    # Process each node
    enriched_count = 0
    for i, node in enumerate(nodes):
        # Use display_name as the query
        display_name = node.get("display_name", "")
        if not display_name:
            continue

        # Also include body snippet if available for better matching
        body = node.get("body", "")
        query = display_name
        if body:
            # Use first few lines of body for context
            body_lines = body.split("\n")[:5]
            query = f"{display_name} {' '.join(body_lines)}"

        # Search for similar lemmas
        results = searcher.search(query, top_k=top_k + 1)  # +1 to exclude self

        # Build similar_lemmas list, excluding the node itself
        similar_lemmas = []
        for lemma, score in results:
            # Skip if it's the same lemma (by name)
            if lemma.name == display_name:
                continue

            similar_lemmas.append(
                {
                    "name": lemma.name,
                    "score": round(score, 3),
                    "file_path": lemma.file_path,
                    "line_number": lemma.line_number,
                    "signature": lemma.signature,
                }
            )

            if len(similar_lemmas) >= top_k:
                break

        # Add to node
        if similar_lemmas:
            node["similar_lemmas"] = similar_lemmas
            enriched_count += 1

        # Progress indicator
        if (i + 1) % 100 == 0 or i + 1 == len(nodes):
            print(f"   Processed {i + 1}/{len(nodes)} nodes...", end="\r")

    print()
    print()

    # Save the enriched graph
    print(f"💾 Saving enriched graph to: {output_file}")
    try:
        with open(output_file, "w") as f:
            json.dump(graph, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving graph: {e}")
        return 1

    print()
    print("=" * 70)
    print("✅ Graph enrichment complete!")
    print("=" * 70)
    print(f"\n   Nodes processed: {len(nodes)}")
    print(f"   Nodes with similar lemmas: {enriched_count}")
    print(f"   Output: {output_file}")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser"""
    parser = argparse.ArgumentParser(description="Semantic lemma search for Verus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate SCIP command
    generate_parser = subparsers.add_parser("generate-scip", help="Generate SCIP JSON from project")
    generate_parser.add_argument(
        "project_dir", help="Project directory (where to run verus-analyzer)"
    )
    generate_parser.add_argument(
        "-o",
        "--output",
        help="Output SCIP JSON file (default: <project>_scip.json in project dir)",
    )

    # Index command
    index_parser = subparsers.add_parser("index", help="Build lemma index from SCIP data")
    index_parser.add_argument("scip_file", help="Path to SCIP JSON file")
    index_parser.add_argument(
        "-o", "--output", help="Output index file (default: lemma_index.json)"
    )
    index_parser.add_argument(
        "-r", "--repo-root", help="Repository root (default: SCIP file directory)"
    )
    index_parser.add_argument(
        "--no-embeddings",
        dest="embeddings",
        action="store_false",
        default=True,
        help="Skip computing embeddings (keyword search only)",
    )
    index_parser.add_argument(
        "--generate-scip",
        action="store_true",
        help="Generate SCIP file first if it doesn't exist",
    )
    index_parser.add_argument(
        "--fill-from",
        dest="fill_from",
        help="Fill empty specs from a reference index (default: vstd_lemma_index.json if found)",
    )
    index_parser.add_argument(
        "--no-fill",
        action="store_true",
        help="Don't fill empty specs from vstd (skip default vstd fill)",
    )
    index_parser.add_argument(
        "--path-filter",
        dest="path_filter",
        default=None,
        help="Only index files matching this prefix (empty string = all files)",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for lemmas")
    search_parser.add_argument("query", help="Search query (natural language)")
    search_parser.add_argument("index_file", help="Path to lemma index file")
    search_parser.add_argument(
        "-k", "--top-k", type=int, default=10, help="Number of results (default: 10)"
    )

    # Similar command - find lemmas similar to a given lemma
    similar_parser = subparsers.add_parser(
        "similar", help="Find lemmas similar to a given lemma (by name)"
    )
    similar_parser.add_argument("lemma_name", help="Name of the lemma to find similar lemmas for")
    similar_parser.add_argument("index_file", help="Path to lemma index file")
    similar_parser.add_argument(
        "-k", "--top-k", type=int, default=5, help="Number of results (default: 5)"
    )

    # Detect duplicates command
    dup_parser = subparsers.add_parser(
        "detect-duplicates", help="Detect duplicate and redundant lemmas"
    )
    dup_parser.add_argument("index_file", help="Path to lemma index file")
    dup_parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=0.75,
        help="Cosine similarity threshold (default: 0.75)",
    )
    dup_parser.add_argument("-o", "--output", help="Output JSON file for results")
    dup_parser.add_argument(
        "--similar",
        action="store_true",
        help="Also detect similar patterns (high semantic similarity, potential refactoring)",
    )
    dup_parser.add_argument(
        "--similar-threshold",
        type=float,
        default=0.90,
        help="Threshold for similar pattern detection (default: 0.90)",
    )

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive search mode")
    interactive_parser.add_argument("index_file", help="Path to lemma index file")

    # Setup vstd command
    setup_vstd_parser = subparsers.add_parser(
        "setup-vstd", help="Clone Verus repository to access vstd"
    )
    setup_vstd_parser.add_argument(
        "target_dir",
        nargs="?",
        default="./verus",
        help="Where to clone Verus (default: ./verus)",
    )

    # Add vstd command
    add_vstd_parser = subparsers.add_parser("add-vstd", help="Add vstd lemmas to existing index")
    add_vstd_parser.add_argument("verus_scip_file", help="Path to Verus SCIP JSON file")
    add_vstd_parser.add_argument("base_index_file", help="Path to your existing lemma index")
    add_vstd_parser.add_argument(
        "-o", "--output", help="Output file (default: overwrites base index)"
    )
    add_vstd_parser.add_argument(
        "-r",
        "--verus-root",
        help="Verus repository root (default: SCIP file directory)",
    )

    # Fill specs command
    fill_parser = subparsers.add_parser(
        "fill-specs", help="Fill empty requires/ensures from a reference index (e.g., vstd)"
    )
    fill_parser.add_argument("index_file", help="Path to lemma index to update")
    fill_parser.add_argument(
        "reference_index", help="Path to reference index (e.g., vstd_lemma_index.json)"
    )
    fill_parser.add_argument("-o", "--output", help="Output file (default: overwrites input index)")

    # Enrich graph command
    enrich_parser = subparsers.add_parser(
        "enrich-graph", help="Enrich a call graph JSON with similar lemmas for each node"
    )
    enrich_parser.add_argument(
        "graph_file", help="Path to the call graph JSON file (from scip-callgraph)"
    )
    enrich_parser.add_argument("index_file", help="Path to the lemma index file")
    enrich_parser.add_argument(
        "-o", "--output", help="Output file (default: overwrites input graph)"
    )
    enrich_parser.add_argument(
        "-k", "--top-k", type=int, default=3, help="Number of similar lemmas per node (default: 3)"
    )

    return parser


def main() -> None:
    """Main entry point for CLI"""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "generate-scip":
        sys.exit(cmd_generate_scip(args))
    elif args.command == "index":
        sys.exit(cmd_index(args))
    elif args.command == "search":
        sys.exit(cmd_search(args))
    elif args.command == "similar":
        sys.exit(cmd_similar(args))
    elif args.command == "detect-duplicates":
        sys.exit(cmd_detect_duplicates(args))
    elif args.command == "interactive":
        sys.exit(cmd_interactive(args))
    elif args.command == "setup-vstd":
        sys.exit(cmd_setup_vstd(args))
    elif args.command == "add-vstd":
        sys.exit(cmd_add_vstd(args))
    elif args.command == "fill-specs":
        sys.exit(cmd_fill_specs(args))
    elif args.command == "enrich-graph":
        sys.exit(cmd_enrich_graph(args))
