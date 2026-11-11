# src/optimizer/graph.py
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from optimizer.nodes.scanner import (
    make_judge_node,
    merge_and_rank,
    profile_node,
    report_node,
    static_node,
)
from optimizer.state import ScannerState


def build_graph(llm: BaseChatModel):
    """Scanner pipeline: profile -> static -> merge -> judge -> report."""
    g = StateGraph(ScannerState)

    g.add_node("profile", profile_node)
    g.add_node("static", static_node)
    g.add_node("merge", merge_and_rank)
    g.add_node("judge", make_judge_node(llm))   # LLM is injected here
    g.add_node("report", report_node)

    g.add_edge(START, "profile")
    g.add_edge("profile", "static")
    g.add_edge("static", "merge")
    g.add_edge("merge", "judge")
    g.add_edge("judge", "report")
    g.add_edge("report", END)

    return g.compile()