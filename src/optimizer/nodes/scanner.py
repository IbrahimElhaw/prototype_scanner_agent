# src/optimizer/nodes/scanner.py
from langchain_core.messages import SystemMessage, HumanMessage

from optimizer.state import Candidate, Judgment, ProfileRow, ScannerState, StaticRow


from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from optimizer.config import Config
import json
from pathlib import Path

from optimizer.tools.profiler import profile_workload
from optimizer.tools.static_analysis import analyze_package

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
    config = state["config"]
    static_rows = state["static_rows"]
    table: dict[tuple, Candidate] = {}

    for p in state["profile_rows"]:
        owner = _find_owner(p, static_rows)
        if owner is None:
            continue

        key = (owner["file"], owner["name"], owner["lineno"])
        if key not in table:
            table[key] = Candidate(
                file=owner["file"],
                name=owner["name"],
                lineno=owner["lineno"],
                end_lineno=owner["end_lineno"],
                calls=0,
                tottime=0.0,
                cumtime=0.0,
                complexity=owner["complexity"],
                patterns=owner["patterns"],
                score=0.0,
            )

        c = table[key]
        c["tottime"] += p["tottime"]              # nested <genexpr>/<lambda> time joins its owner
        c["cumtime"] = max(c["cumtime"], p["cumtime"])
        if p["name"] == owner["name"]:            # the function itself, not a nested helper
            c["calls"] = p["calls"]

    ranked = sorted(table.values(), key=lambda c: c["tottime"], reverse=True)
    for c in ranked:
        c["score"] = c["tottime"]                 # ranking is by measured time only

    return {"candidates": ranked[: config.top_n]}


class AnswerStructure(BaseModel):
    """Structured answer we ask the LLM for (kept small on purpose)."""
    idea: str = Field(description="At most two sentences: a specific improvement, or 'No clear improvement'")
    improvable: bool = Field(description="True if this function's runtime can likely be reduced without changing its results")
    confidence: Literal["low", "medium", "high"]


_SYSTEM_PROMPT = (
    "You are a Python performance reviewer. You receive one function with measured profiling data "
    "and static hints. The static hints are guesses and may be wrong; the measured time is the evidence. "
    "Decide whether the runtime of this function can likely be reduced WITHOUT changing its behavior "
    "(same results, same ordering, same return types). "
    "A function that takes only a tiny share of the total time is rarely worth optimizing. "
    " Be concise. Do not rewrite the code. Set improvable "
    "to true ONLY if you can name a specific change (for example a better algorithm or data structure) that"
    " makes the function do less work. If you cannot, write 'No clear improvement' as the idea and set improvable to false."
)


def _read_source(config: Config, c: Candidate) -> str:
    lines = (config.package_dir / c["file"]).read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[c["lineno"] - 1 : c["end_lineno"]])


def _build_prompt(c: Candidate, source: str, share: float) -> str:
    hints = ", ".join(c["patterns"]) or "none"
    return (
        f"Function `{c['name']}` in `{c['file']}`.\n"
        f"Measured self time: {c['tottime']:.4f}s over {c['calls']} call(s) "
        f"({share:.1%} of the total measured project time).\n"
        f"Cyclomatic complexity: {c['complexity']}. Static hints: {hints}.\n\n"
        f"```python\n{source}\n```"
    )


def make_judge_node(llm: BaseChatModel):
    """Build the judge node. The LLM is injected, so it can be swapped or mocked."""
    judge = llm.with_structured_output(AnswerStructure)

    def judge_node(state: ScannerState) -> dict:
        config = state["config"]
        judgments: list[Judgment] = []
        errors: list[str] = []
        total_time = sum(p["tottime"] for p in state["profile_rows"]) or 1.0

        for c in state["candidates"]:

            share = c["tottime"] / total_time
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(c, _read_source(config, c), share)),
            ]
            answer, last_error = None, ""
            for _attempt in range(2):  # one retry
                try:
                    answer = judge.invoke(messages)
                    break
                except Exception as exc:  # small local models sometimes return invalid JSON
                    last_error = str(exc)

            if answer is None:
                errors.append(f"judge failed for {c['file']}:{c['name']}: {last_error}")
                continue

            judgments.append(
                Judgment(
                    file=c["file"],
                    name=c["name"],
                    improvable=answer.improvable,
                    idea=answer.idea,
                    confidence=answer.confidence,
                )
            )

        return {"judgments": judgments, "errors": errors}

    return judge_node


def profile_node(state: ScannerState) -> dict:
    try:
        return {"profile_rows": profile_workload(state["config"])}
    except RuntimeError as exc:
        return {"profile_rows": [], "errors": [f"profile failed: {exc}"]}


def static_node(state: ScannerState) -> dict:
    try:
        return {"static_rows": analyze_package(state["config"])}
    except (OSError, SyntaxError) as exc:
        return {"static_rows": [], "errors": [f"static analysis failed: {exc}"]}


def report_node(state: ScannerState) -> dict:
    """Write the ranked candidates, each with its LLM judgment, to a JSON file."""
    verdicts = {(j["file"], j["name"]): j for j in state.get("judgments", [])}
    items = [
        {**c, "judgment": verdicts.get((c["file"], c["name"]))}
        for c in state.get("candidates", [])
    ]
    report = {"candidates": items, "errors": state.get("errors", [])}

    path = Path(state["config"].output_path)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"report_path": str(path.resolve())}