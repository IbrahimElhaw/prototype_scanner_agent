import json
from pathlib import Path

from scanner.state import ScannerState
from scanner.tools.profiler import profile_workload
from scanner.tools.static_analysis import analyze_package


def profile_node(state: ScannerState) -> dict:
    try:
        rows, failures = profile_workload(state["config"])
    except (RuntimeError, OSError, ValueError) as exc:
        return {"profile_rows": [], "errors": [f"profile failed: {exc}"]}
    errors = [f"profile failed for {name}:\n{err}" for name, err in failures.items()]
    return {"profile_rows": rows, "errors": errors}

def static_node(state: ScannerState) -> dict:
    try:
        return {"static_rows": analyze_package(state["config"])}
    except (OSError, SyntaxError) as exc:
        return {"static_rows": [], "errors": [f"static analysis failed: {exc}"]}


def report_node(state: ScannerState) -> dict:
    """Write the ranked candidates, each with its LLM judgment, to a JSON file."""
    verdicts = {(j["file"], j["name"]): j for j in state.get("judgments", [])}
    items = [{**c, "judgment": verdicts.get((c["file"], c["name"]))} for c in state.get("candidates", [])]
    report = {"candidates": items, "errors": state.get("errors", [])}

    path = Path(state["config"].output_path)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"report_path": str(path.resolve())}