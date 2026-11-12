# src/optimizer/nodes/merge.py
from optimizer.state import Candidate, ProfileRow, ScannerState, StaticRow


def _find_owner(row: ProfileRow, static_rows: list[StaticRow]) -> StaticRow | None:
    """Innermost function (by line range) in the same file that contains this profile row."""
    best = None
    for s in static_rows:
        if s["file"] == row["file"] and s["lineno"] <= row["lineno"] <= s["end_lineno"]:
            if best is None or s["lineno"] > best["lineno"]:
                best = s
    return best


def merge_and_rank(state: ScannerState) -> dict:
    """Merge profile + static rows into one table, ranked by measured time."""
    table: dict[tuple, Candidate] = {}

    for p in state["profile_rows"]:
        owner = _find_owner(p, state["static_rows"])
        if owner is None:
            continue

        key = (owner["file"], owner["name"], owner["lineno"])
        c = table.setdefault(key, Candidate(
            file=owner["file"], name=owner["name"], lineno=owner["lineno"],
            end_lineno=owner["end_lineno"], calls=0, tottime=0.0, cumtime=0.0,
            complexity=owner["complexity"], patterns=owner["patterns"], score=0.0,
        ))
        c["tottime"] += p["tottime"]              # nested <genexpr>/<lambda> time joins its owner
        c["cumtime"] = max(c["cumtime"], p["cumtime"])
        if p["name"] == owner["name"]:            # the function itself, not a nested helper
            c["calls"] = p["calls"]

    ranked = sorted(table.values(), key=lambda c: c["tottime"], reverse=True)
    for c in ranked:
        c["score"] = c["tottime"]                 # ranking is by measured time only
    return {"candidates": ranked[: state["config"].top_n]}