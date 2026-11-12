import operator
from typing import Annotated, TypedDict

from optimizer.config import Config


class ProfileRow(TypedDict):
    """One function as measured by cProfile (project files only)."""
    file: str        # path relative to the target package
    name: str
    lineno: int
    calls: int
    tottime: float   # self time, seconds
    cumtime: float   # self time + callees, seconds


class StaticRow(TypedDict):
    """One function as seen by static analysis (radon + AST)."""
    file: str
    name: str
    lineno: int
    complexity: int          # radon cyclomatic complexity
    patterns: list[str]      # e.g. ["nested_loop", "re_compile_in_loop"]
    lineno: int
    end_lineno: int          # last line of the function (used to attach <genexpr> time to its parent)


class Candidate(TypedDict):
    """Merged row: profile + static signals + our deterministic score."""
    file: str
    name: str
    lineno: int
    end_lineno: int
    calls: int
    tottime: float
    cumtime: float
    complexity: int
    patterns: list[str]
    score: float


class Judgment(TypedDict):
    """The LLM's verdict on one candidate."""
    file: str
    name: str
    improvable: bool
    idea: str
    confidence: str          # "low" | "medium" | "high"


class ScannerState(TypedDict, total=False):
    config: Config
    profile_rows: list[ProfileRow]
    static_rows: list[StaticRow]
    candidates: list[Candidate]      # sorted by score, best first
    judgments: list[Judgment]
    errors: Annotated[list[str], operator.add]
    report_path: str