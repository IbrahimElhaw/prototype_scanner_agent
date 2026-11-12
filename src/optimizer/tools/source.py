# src/optimizer/tools/source.py
from pathlib import Path


def read_lines(path: Path, first_line: int, last_line: int) -> str:
    """Return lines first_line..last_line (1-based, inclusive) of a file as one string."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[first_line - 1 : last_line])