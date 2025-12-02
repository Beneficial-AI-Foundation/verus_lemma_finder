"""
Command-line interface for the lemma search tool.
"""

import argparse
import sys
from pathlib import Path

from .indexing import LemmaIndexer, merge_indexes
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
        print(
            "  uv run python -m verus_lemma_finder index <your_project_scip>.json"
        )
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
        print(
            "⚠️  Warning: Base index has embeddings but sentence-transformers not available"
        )
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

    try:
        indexer = LemmaIndexer(scip_file, repo_root, use_embeddings=use_embeddings)
        indexer.build_index()
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
            choice = input(
                "Enter number for details (or press Enter to continue): "
            ).strip()
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


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser"""
    parser = argparse.ArgumentParser(description="Semantic lemma search for Verus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate SCIP command
    generate_parser = subparsers.add_parser(
        "generate-scip", help="Generate SCIP JSON from project"
    )
    generate_parser.add_argument(
        "project_dir", help="Project directory (where to run verus-analyzer)"
    )
    generate_parser.add_argument(
        "-o",
        "--output",
        help="Output SCIP JSON file (default: <project>_scip.json in project dir)",
    )

    # Index command
    index_parser = subparsers.add_parser(
        "index", help="Build lemma index from SCIP data"
    )
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

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for lemmas")
    search_parser.add_argument("query", help="Search query (natural language)")
    search_parser.add_argument("index_file", help="Path to lemma index file")
    search_parser.add_argument(
        "-k", "--top-k", type=int, default=10, help="Number of results (default: 10)"
    )

    # Interactive command
    interactive_parser = subparsers.add_parser(
        "interactive", help="Interactive search mode"
    )
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
    add_vstd_parser = subparsers.add_parser(
        "add-vstd", help="Add vstd lemmas to existing index"
    )
    add_vstd_parser.add_argument("verus_scip_file", help="Path to Verus SCIP JSON file")
    add_vstd_parser.add_argument(
        "base_index_file", help="Path to your existing lemma index"
    )
    add_vstd_parser.add_argument(
        "-o", "--output", help="Output file (default: overwrites base index)"
    )
    add_vstd_parser.add_argument(
        "-r",
        "--verus-root",
        help="Verus repository root (default: SCIP file directory)",
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
    elif args.command == "interactive":
        sys.exit(cmd_interactive(args))
    elif args.command == "setup-vstd":
        sys.exit(cmd_setup_vstd(args))
    elif args.command == "add-vstd":
        sys.exit(cmd_add_vstd(args))
