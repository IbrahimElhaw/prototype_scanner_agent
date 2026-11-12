from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from optimizer.state import Candidate, Judgment, ScannerState
from optimizer.tools.source import read_lines


class AnswerStructure(BaseModel):
    """Structured answer we ask the LLM for (kept small on purpose)."""
    idea: str = Field(description="At most two sentences: the specific improvement, or why none applies")
    improvable: bool = Field(description="True if this function's runtime can likely be reduced without changing its results")
    confidence: Literal["low", "medium", "high"]


_SYSTEM_PROMPT = (
    "You are a Python performance reviewer. You receive one function with measured profiling data "
    "and static hints. The static hints are guesses and may be wrong; the measured time is the evidence. "
    "Decide whether the runtime of this function can likely be reduced WITHOUT changing its behavior "
    "(same results, same ordering, same return types). Examples of possible reductions, not a limit: "
    "a better data structure, a better algorithm, removing duplicated or useless work, "
    "or using a built-in alternative. "
    "A function that takes only a tiny share of the total time is rarely worth optimizing. "
    "Be concise. Do not rewrite the code."
)


def _build_prompt(c: Candidate, source: str, share: float) -> str:
    hints = ", ".join(c["patterns"]) or "none"
    return (
        f"Function `{c['name']}` in `{c['file']}`.\n"
        f"Measured self time: {c['tottime']:.4f}s over {c['calls']} call(s) "
        f"({share:.1%} of the total measured project time).\n"
        f"Cyclomatic complexity: {c['complexity']}. Static hints: {hints}.\n\n"
        f"```python\n{source}\n```"
    )


def _ask(judge, messages, attempts: int = 2):
    """Call the LLM, retrying once. Returns (answer, error)."""
    error = ""
    for _ in range(attempts):
        try:
            return judge.invoke(messages), ""
        except Exception as exc:  # small local models sometimes return invalid JSON
            error = str(exc)
    return None, error


def make_judge_node(llm: BaseChatModel):
    """Build the judge node. The LLM is injected, so it can be swapped or mocked."""
    judge = llm.with_structured_output(AnswerStructure)

    def judge_node(state: ScannerState) -> dict:
        config = state["config"]
        total_time = sum(p["tottime"] for p in state["profile_rows"]) or 1.0
        judgments: list[Judgment] = []
        errors: list[str] = []

        for c in state["candidates"]:
            source = read_lines(config.package_dir / c["file"], c["lineno"], c["end_lineno"])
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(c, source, c["tottime"] / total_time)),
            ]
            answer, error = _ask(judge, messages)
            if answer is None:
                errors.append(f"judge failed for {c['file']}:{c['name']}: {error}")
                continue
            judgments.append(Judgment(file=c["file"], name=c["name"], **answer.model_dump()))

        return {"judgments": judgments, "errors": errors}

    return judge_node