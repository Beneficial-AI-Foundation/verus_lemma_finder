"""
Pytest configuration for verus_lemma_finder tests.
"""

from pathlib import Path


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--index",
        action="store",
        default=str(Path(__file__).parent.parent / "curve25519-dalek_lemma_index.json"),
        help="Path to lemma index file",
    )
