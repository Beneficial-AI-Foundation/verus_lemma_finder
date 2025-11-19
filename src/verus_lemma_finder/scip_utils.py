"""
SCIP-related utilities for generating and processing SCIP data.
"""

import shutil
import subprocess
from pathlib import Path


def check_command_available(command: str) -> bool:
    """Check if a command is available in PATH"""
    return shutil.which(command) is not None


def generate_scip_json(project_dir: Path, output_file: Path) -> bool:
    """
    Generate SCIP JSON by running:
    1. verus-analyzer scip .
    2. scip print --json index.scip > output.json

    Returns True on success, False on failure
    """
    # Validate paths to prevent injection attacks
    try:
        project_dir = project_dir.resolve()
        output_file = output_file.resolve()
    except (OSError, RuntimeError) as e:
        print(f"❌ Error: Invalid path - {e}")
        return False

    if not project_dir.is_dir():
        print(
            f"❌ Error: Project directory does not exist or is not a directory: {project_dir}"
        )
        return False

    print(f"📋 Generating SCIP index for {project_dir}...")

    # Check if required commands are available
    if not check_command_available("verus-analyzer"):
        print("❌ Error: 'verus-analyzer' command not found in PATH")
        print("   Please install verus-analyzer or ensure it's in your PATH")
        return False

    if not check_command_available("scip"):
        print("❌ Error: 'scip' command not found in PATH")
        print("   Please install scip (https://github.com/sourcegraph/scip)")
        return False

    # Step 1: Generate SCIP index
    print("⚙️  Step 1: Running 'verus-analyzer scip .'...")
    try:
        result = subprocess.run(
            ["verus-analyzer", "scip", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            print("❌ Error running verus-analyzer:")
            print(result.stderr)
            return False

        print("✓ SCIP index generated (index.scip)")
    except subprocess.TimeoutExpired:
        print("❌ Error: verus-analyzer timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Error running verus-analyzer: {e}")
        return False

    # Step 2: Convert to JSON
    scip_index_file = project_dir / "index.scip"
    if not scip_index_file.exists():
        print(f"❌ Error: index.scip not found at {scip_index_file}")
        return False

    print("⚙️  Step 2: Converting to JSON with 'scip print --json'...")
    try:
        result = subprocess.run(
            ["scip", "print", "--json", str(scip_index_file)],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout
        )

        if result.returncode != 0:
            print("❌ Error running scip print:")
            print(result.stderr)
            return False

        # Write output to JSON file
        with open(output_file, "w") as f:
            f.write(result.stdout)

        # Check file size
        size_mb = output_file.stat().st_size / 1024 / 1024
        print(f"✓ SCIP JSON generated: {output_file} ({size_mb:.1f} MB)")
        return True

    except subprocess.TimeoutExpired:
        print("❌ Error: scip print timed out (>1 minute)")
        return False
    except Exception as e:
        print(f"❌ Error running scip print: {e}")
        return False


def clone_verus_repo(target_dir: Path) -> bool:
    """Clone the Verus repository"""
    verus_url = "https://github.com/verus-lang/verus.git"

    if target_dir.exists():
        print(f"⚠️  Directory already exists: {target_dir}")
        response = input("Use existing directory? (y/n): ").strip().lower()
        return response == "y"

    print("📥 Cloning Verus repository...")
    print(f"   Source: {verus_url}")
    print(f"   Target: {target_dir}")
    print("   (This may take a few minutes...)")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", verus_url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error cloning repository:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Error: git command not found. Please install git.")
        return False
