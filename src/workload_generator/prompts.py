SYSTEM_PROMPT = """You write input builders for performance benchmarking of Python functions.

You receive one target function. Write ONE Python function (the builder) that creates
valid inputs for it, scaled by an integer n. The builder's name is given in the user message.

Signature: def <builder_name>(n: int):
Return value: a tuple (args, kwargs). args is a tuple, kwargs is a dict.
    return (orders,), {}               # one positional argument
    return (orders, 100), {}           # two positional arguments
    return (), {"orders": orders}      # keyword arguments

Rules:
- n is the SIZE of the main input (list length, string length, number of rows).
  Doubling n must roughly double the amount of data. Never clamp or ignore n.
- Keep the builder's own work proportional to n. Never loop n * n times.
- Put everything inside the builder: no imports, no module-level constants, no try/except.
  `random` is already available; use rng = random.Random(0).
- The classes and project functions listed in the user message are already imported.
  Never redefine a class.
- NEVER call the target function and NEVER reimplement its logic or compute its result.
  Only construct raw inputs.
- Do not guess file or text formats. If the target parses text (CSV lines, ...) and the exact
  format is not visible in its source, call a listed project function that produces that text.
- Make the data exercise the function: if it looks for duplicates, include some; if it filters
  by a threshold, make some items pass and some fail.
- Output ONLY the code of the builder. No markdown fences, no explanations.
- do not write anything except code"""


def build_user_prompt(func,
                      class_infos,
                      helper_infos,
                      builder_name: str) -> str:

    parts = [
        f"Target function: {func.qualified_name}",
        f"Signature: {func.signature}",
    ]
    if func.docstring:
        parts.append(f"Docstring: {func.docstring}")
    parts.append(f"Source:\n{func.source}")
    for c in class_infos:
        parts.append(f"Class {c.name} (already imported):\n{c.source}")
    if helper_infos:
        lines = []
        for h in helper_infos:
            short = h.qualified_name.split(":")[1]
            doc = h.docstring.splitlines()[0] if h.docstring else ""
            lines.append(f"- {short}{h.signature}  # {doc}")
        parts.append("Project functions you MAY call to build inputs (already imported):\n" + "\n".join(lines))
    parts.append(f"Write the builder named: {builder_name}")
    return "\n\n".join(parts)