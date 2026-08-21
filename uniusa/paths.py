"""Repository paths shared by library modules and command-line entry points."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
DERIVED = ROOT / "derived"
