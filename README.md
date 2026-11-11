# Runtime Scanner Agent

A LangGraph-based scanner that finds the functions most worth optimizing in an existing Python project. It ranks functions by **measured runtime**, adds **static code hints**, and asks a local LLM for a short advisory verdict on the top candidates.

## Pipeline

```
profile  ->  static  ->  merge  ->  judge  ->  report
```

- **profile** (deterministic): runs the target's workload under `cProfile` in a subprocess and keeps timings for functions of the target package only.
- **static** (deterministic): uses `ast` and `radon` to collect each function's line range, cyclomatic complexity, and a `nested_loop` hint (comprehensions and generator expressions count as loops).
- **merge** (deterministic): joins both tables. Anonymous entries such as `<genexpr>` are attributed to their enclosing function using line ranges, and candidates are ranked by measured self time only.
- **judge** (LLM): one call per top-N candidate. The prompt contains the source, time share, call count, complexity, and hints (labeled as guesses). The model returns a validated object with `idea`, `improvable`, and `confidence`. Failed calls are retried once, then recorded as errors without stopping the run.
- **report**: writes the ranked candidates with their verdicts to a JSON file.

## Design principles

- **Evidence before opinion:** ranking uses measured time only; hints and the LLM are advisory and never reorder results.
- **Generic by construction:** nothing in the logic or prompts refers to specific functions or projects.
- **Swappable model:** the LLM is built from the config in one place and injected into the judge node, so a small local model can be replaced by a larger one without touching the graph.
- **Fail soft:** errors are collected in the shared state instead of aborting the pipeline.

## Structure

```
src/optimizer/
  config.py   state.py   llm.py   graph.py   main.py
  tools/      profiler.py, static_analysis.py
  nodes/      scanner.py
target/       the Python project being analyzed
```

All settings (target project, workload script, top-N, model, output path) live in one dataclass in `config.py`.

## Stack

Python 3.12, LangGraph, LangChain (Ollama), Pydantic, radon, `cProfile`/`pstats`/`ast`. The LLM runs locally through Ollama.
