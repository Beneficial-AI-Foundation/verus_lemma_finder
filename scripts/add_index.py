#!/usr/bin/env python3
"""
Script to add a new lemma index to verus_lemma_finder.

Usage:
    # Interactive mode (guided prompts)
    python scripts/add_index.py

    # Non-interactive mode (command-line arguments)
    python scripts/add_index.py --name myproject --path /path/to/project

    # With all options
    python scripts/add_index.py --name myproject --path /path/to/project \
        --scip /path/to/scip.json \
        --github-url https://github.com/user/repo \
        --no-demo

This script:
1. Generates a SCIP index from your Verus project (optional)
2. Builds a semantic search index with embeddings
3. Optionally adds it to the demo server
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Add src to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Global flag for interactive mode
INTERACTIVE = True


def print_header(text: str) -> None:
    """Print a formatted header."""
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)
    print()


def print_step(num: int, text: str) -> None:
    """Print a step indicator."""
    print(f"\n📌 Step {num}: {text}")
    print("-" * 50)


def prompt(text: str, default: str = "") -> str:
    """Prompt user for input with optional default (interactive mode only)."""
    if not INTERACTIVE:
        return default
    if default:
        result = input(f"{text} [{default}]: ").strip()
        return result if result else default
    return input(f"{text}: ").strip()


def prompt_yes_no(text: str, default: bool = True) -> bool:
    """Prompt user for yes/no answer (interactive mode only)."""
    if not INTERACTIVE:
        return default
    default_str = "Y/n" if default else "y/N"
    result = input(f"{text} [{default_str}]: ").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


def check_scip_file(path: Path) -> bool:
    """Check if a SCIP JSON file is valid."""
    if not path.exists():
        return False
    try:
        with open(path) as f:
            data = json.load(f)
        return "documents" in data
    except (OSError, json.JSONDecodeError):
        return False


def generate_scip(project_dir: Path, output_file: Path) -> bool:
    """Generate SCIP index using verus-analyzer."""
    print(f"\n🔧 Generating SCIP index for {project_dir}...")
    print("   Running: verus-analyzer scip .")

    try:
        # Run verus-analyzer scip
        result = subprocess.run(
            ["verus-analyzer", "scip", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"❌ verus-analyzer failed: {result.stderr}")
            return False

        # Convert to JSON
        scip_file = project_dir / "index.scip"
        if not scip_file.exists():
            print(f"❌ index.scip not created at {scip_file}")
            return False

        print("   Running: scip print --json index.scip")
        result = subprocess.run(
            ["scip", "print", "--json", str(scip_file)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"❌ scip print failed: {result.stderr}")
            return False

        # Save JSON output
        with open(output_file, "w") as f:
            f.write(result.stdout)

        print(f"✅ SCIP index saved to {output_file}")
        return True

    except FileNotFoundError as e:
        print(f"❌ Command not found: {e}")
        print("\nMake sure verus-analyzer and scip are installed:")
        print("  - verus-analyzer: https://github.com/verus-lang/verus-analyzer")
        print("  - scip: https://github.com/sourcegraph/scip")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False


def build_index(
    scip_file: Path,
    repo_root: Path,
    output_file: Path,
    project_name: str,
    use_embeddings: bool = True,
    path_filter: str = ""
) -> int:
    """Build the semantic search index."""
    print(f"\n🔧 Building index from {scip_file}...")

    try:
        from verus_lemma_finder.indexing import LemmaIndexer

        indexer = LemmaIndexer(
            scip_file=scip_file,
            repo_root=repo_root,
            use_embeddings=use_embeddings,
            source=project_name,
            path_filter=path_filter if path_filter else None
        )

        lemmas = indexer.build_index()

        if not lemmas:
            print("❌ No lemmas found in the SCIP index")
            print("   Make sure your project contains proof functions (lemma_, axiom_, proof fn)")
            return 0

        indexer.save_index(output_file)
        print(f"✅ Index saved to {output_file}")

        return len(lemmas)

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you've installed the package: uv pip install -e .")
        return 0
    except Exception as e:
        print(f"❌ Error building index: {e}")
        return 0


def add_to_demo_server(
    project_name: str,
    github_url: str,
    branch: str,
    path_prefix: str,
    index_file: str,
    force: bool = False
) -> bool:
    """Add the project to the demo server configuration."""
    server_file = PROJECT_ROOT / "demo" / "server.py"

    if not server_file.exists():
        print(f"❌ Server file not found: {server_file}")
        return False

    # Read current server.py
    content = server_file.read_text()

    # Check if project already exists
    if f'"{project_name}"' in content:
        print(f"⚠️  Project '{project_name}' already exists in server.py")
        if not force and not prompt_yes_no("Overwrite existing configuration?", default=False):
            return False

    # Create new entry
    new_entry = f'''    "{project_name}": {{
        "url": "{github_url}",
        "branch": "{branch}",
        "path_prefix": "{path_prefix}",
        "index_file": "{index_file}"
    }}'''

    # Find GITHUB_REPOS and add entry
    import re
    pattern = r'(GITHUB_REPOS\s*=\s*\{[^}]+)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        # Add new entry before closing brace
        insert_pos = match.end()
        # Check if we need a comma
        before = content[:insert_pos].rstrip()
        new_entry = ',\n' + new_entry if not before.endswith(',') else '\n' + new_entry

        new_content = content[:insert_pos] + new_entry + content[insert_pos:]
        server_file.write_text(new_content)
        print(f"✅ Added '{project_name}' to demo server configuration")
        return True
    else:
        print("❌ Could not find GITHUB_REPOS in server.py")
        print("   You may need to add the configuration manually")
        return False


def run_interactive() -> int:
    """Run in interactive mode with prompts."""
    print_header("🚀 Add New Index to verus_lemma_finder")

    print("This script will help you create a searchable index for your Verus project.")
    print("You'll need:")
    print("  • A Verus project with proof functions (lemma_, axiom_, proof fn)")
    print("  • verus-analyzer installed (for generating SCIP)")
    print("  • scip CLI tool installed")
    print()

    # Step 1: Get project information
    print_step(1, "Project Information")

    project_name = prompt("Project name (e.g., 'myproject')")
    if not project_name:
        print("❌ Project name is required")
        return 1

    # Sanitize project name
    project_name = project_name.lower().replace(" ", "_").replace("-", "_")

    project_dir = Path(prompt("Path to your Verus project directory"))
    if not project_dir.exists():
        print(f"❌ Directory not found: {project_dir}")
        return 1

    project_dir = project_dir.resolve()

    # Step 2: SCIP Index
    print_step(2, "SCIP Index")

    scip_file = find_or_generate_scip(project_dir, project_name)
    if scip_file is None:
        return 1

    # Step 3: Build Index
    print_step(3, "Build Semantic Search Index")

    use_embeddings = prompt_yes_no("Use embeddings for semantic search? (recommended)", default=True)

    # Path filter (for mono-repos)
    print("\nPath filter (optional):")
    print("  If your project is part of a mono-repo, you can filter to specific paths.")
    print("  Leave empty to index all proof functions.")
    path_filter = prompt("Path filter (e.g., 'src/mylib')", "")

    # Output file
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    output_file = data_dir / f"{project_name}_lemma_index.json"

    print(f"\n📦 Output: {output_file}")

    lemma_count = build_index(
        scip_file=scip_file,
        repo_root=project_dir,
        output_file=output_file,
        project_name=project_name,
        use_embeddings=use_embeddings,
        path_filter=path_filter
    )

    if lemma_count == 0:
        return 1

    print(f"\n✅ Indexed {lemma_count} lemmas!")

    # Step 4: Demo Server (optional)
    print_step(4, "Demo Server Configuration (Optional)")

    add_to_demo = prompt_yes_no("Add this index to the demo web server?", default=True)
    github_url = ""

    if add_to_demo:
        print("\nGitHub repository information (for 'View on GitHub' links):")
        github_url = prompt("GitHub URL (e.g., 'https://github.com/user/repo')", "")
        branch = prompt("Branch name", "main")
        path_prefix = prompt("Path prefix in repo (e.g., 'src/')", "")

        relative_index = f"data/{project_name}_lemma_index.json"

        if github_url:
            add_to_demo_server(
                project_name=project_name,
                github_url=github_url,
                branch=branch,
                path_prefix=path_prefix,
                index_file=relative_index
            )
        else:
            print("⚠️  Skipping demo server (no GitHub URL provided)")

    # Summary
    print_summary(project_name, output_file, lemma_count, add_to_demo and bool(github_url))
    return 0


def find_or_generate_scip(project_dir: Path, project_name: str) -> Path | None:
    """Find existing SCIP file or generate a new one."""
    default_scip = project_dir / f"{project_name}_index_scip.json"
    existing_scip = None

    for candidate in [
        project_dir / "index_scip.json",
        project_dir / f"{project_name}_index_scip.json",
        project_dir / f"{project_dir.name}_scip.json",
        project_dir / f"{project_dir.name}_index_scip.json",
    ]:
        if check_scip_file(candidate):
            existing_scip = candidate
            break

    if existing_scip:
        print(f"📄 Found existing SCIP file: {existing_scip}")
        use_existing = prompt_yes_no("Use this existing SCIP file?", default=True)
        if use_existing:
            return existing_scip
        else:
            scip_path = prompt("Path to SCIP JSON file", str(default_scip))
            return Path(scip_path) if scip_path else None
    else:
        print("No existing SCIP file found.")
        generate_new = prompt_yes_no("Generate SCIP index using verus-analyzer?", default=True)

        if generate_new:
            scip_file = default_scip
            if not generate_scip(project_dir, scip_file):
                print("\n⚠️  SCIP generation failed. You can:")
                print("   1. Generate it manually:")
                print(f"      cd {project_dir}")
                print("      verus-analyzer scip .")
                print(f"      scip print --json index.scip > {scip_file.name}")
                print("   2. Provide an existing SCIP JSON file")

                scip_path = prompt("\nPath to SCIP JSON file (or press Enter to exit)")
                if not scip_path or not check_scip_file(Path(scip_path)):
                    print("❌ Valid SCIP file required")
                    return None
                return Path(scip_path)
            return scip_file
        else:
            scip_path = prompt("Path to SCIP JSON file")
            scip_file = Path(scip_path)
            if not check_scip_file(scip_file):
                print(f"❌ Invalid SCIP file: {scip_file}")
                return None
            return scip_file


def print_summary(project_name: str, output_file: Path, lemma_count: int, demo_added: bool) -> None:
    """Print the final summary."""
    print_header("✅ Setup Complete!")

    print(f"Index created: {output_file}")
    print(f"Lemmas indexed: {lemma_count}")
    print()
    print("You can now search your project:")
    print()
    print("  # CLI search")
    print(f"  uv run python -m verus_lemma_finder search \"your query\" {output_file}")
    print()
    print("  # Interactive mode")
    print(f"  uv run python -m verus_lemma_finder interactive {output_file}")

    if demo_added:
        print()
        print("  # Web demo (after restarting server)")
        print("  ./demo/start_demo.sh")
        print(f"  # Then select '{project_name}' in the dropdown")


def run_non_interactive(args: argparse.Namespace) -> int:
    """Run in non-interactive mode with command-line arguments."""
    print_header("🚀 Add New Index to verus_lemma_finder (non-interactive)")

    # Validate required arguments
    project_name = args.name.lower().replace(" ", "_").replace("-", "_")
    project_dir = Path(args.path).resolve()

    if not project_dir.exists():
        print(f"❌ Directory not found: {project_dir}")
        return 1

    print(f"📦 Project: {project_name}")
    print(f"📂 Path: {project_dir}")

    # Step 1: SCIP Index
    if args.scip:
        scip_file = Path(args.scip)
        if not check_scip_file(scip_file):
            print(f"❌ Invalid SCIP file: {scip_file}")
            return 1
        print(f"📄 Using SCIP: {scip_file}")
    else:
        # Try to find existing or generate new
        scip_file = None
        for candidate in [
            project_dir / "index_scip.json",
            project_dir / f"{project_name}_index_scip.json",
            project_dir / f"{project_dir.name}_scip.json",
            project_dir / f"{project_dir.name}_index_scip.json",
        ]:
            if check_scip_file(candidate):
                scip_file = candidate
                print(f"📄 Found existing SCIP: {scip_file}")
                break

        if scip_file is None:
            # Generate new SCIP
            scip_file = project_dir / f"{project_name}_index_scip.json"
            print("📄 Generating SCIP index...")
            if not generate_scip(project_dir, scip_file):
                return 1

    # Step 2: Build Index
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    output_file = Path(args.output) if args.output else data_dir / f"{project_name}_lemma_index.json"

    use_embeddings = not args.no_embeddings
    path_filter = args.path_filter or ""

    print(f"📦 Output: {output_file}")
    print(f"🔮 Embeddings: {'yes' if use_embeddings else 'no'}")
    if path_filter:
        print(f"🔍 Path filter: {path_filter}")

    lemma_count = build_index(
        scip_file=scip_file,
        repo_root=project_dir,
        output_file=output_file,
        project_name=project_name,
        use_embeddings=use_embeddings,
        path_filter=path_filter
    )

    if lemma_count == 0:
        return 1

    print(f"\n✅ Indexed {lemma_count} lemmas!")

    # Step 3: Demo Server (optional)
    demo_added = False
    if not args.no_demo and args.github_url:
        relative_index = f"data/{project_name}_lemma_index.json"
        demo_added = add_to_demo_server(
            project_name=project_name,
            github_url=args.github_url,
            branch=args.branch or "main",
            path_prefix=args.github_path_prefix or "",
            index_file=relative_index,
            force=args.force
        )

    # Summary
    print_summary(project_name, output_file, lemma_count, demo_added)
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Add a new lemma index to verus_lemma_finder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (guided prompts)
  python scripts/add_index.py

  # Non-interactive mode with defaults
  python scripts/add_index.py --name myproject --path /path/to/project

  # With GitHub integration for demo server
  python scripts/add_index.py --name myproject --path /path/to/project \\
      --github-url https://github.com/user/repo

  # Using existing SCIP file
  python scripts/add_index.py --name myproject --path /path/to/project \\
      --scip /path/to/existing_scip.json

  # Skip demo server integration
  python scripts/add_index.py --name myproject --path /path/to/project --no-demo
"""
    )

    parser.add_argument(
        "--name", "-n",
        help="Project name (e.g., 'myproject')"
    )
    parser.add_argument(
        "--path", "-p",
        help="Path to your Verus project directory"
    )
    parser.add_argument(
        "--scip", "-s",
        help="Path to existing SCIP JSON file (optional, will generate if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output index file path (default: data/<name>_lemma_index.json)"
    )
    parser.add_argument(
        "--path-filter",
        help="Filter to specific paths within the project (for mono-repos)"
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip computing embeddings (keyword search only)"
    )
    parser.add_argument(
        "--github-url",
        help="GitHub repository URL (for 'View on GitHub' links in demo)"
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="GitHub branch name (default: main)"
    )
    parser.add_argument(
        "--github-path-prefix",
        help="Path prefix in GitHub repo (e.g., 'src/')"
    )
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="Skip adding to demo server"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite existing demo server configuration"
    )

    return parser


def main() -> int:
    """Main entry point."""
    global INTERACTIVE

    parser = create_parser()
    args = parser.parse_args()

    # Determine if we should run in interactive mode
    if args.name and args.path:
        # Non-interactive mode - required args provided
        INTERACTIVE = False
        return run_non_interactive(args)
    elif args.name or args.path or args.scip:
        # Partial args provided - error
        print("❌ Error: --name and --path are both required for non-interactive mode")
        print("   Run without arguments for interactive mode, or provide both --name and --path")
        parser.print_usage()
        return 1
    else:
        # Interactive mode
        INTERACTIVE = True
        return run_interactive()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(130)
