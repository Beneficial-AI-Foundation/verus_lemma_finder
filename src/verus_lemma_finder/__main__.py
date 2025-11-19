"""
Entry point for running the package as a module.

Usage:
    python -m verus_lemma_finder search "query" index.json
    uv run python -m verus_lemma_finder search "query" index.json
"""

from .cli import main

if __name__ == "__main__":
    main()
