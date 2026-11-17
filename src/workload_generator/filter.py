import ast
from dataclasses import dataclass

from extractor import FunctionInfo

# TODO: Discuss this with team
""" This words indicates that the function would not be scanned for the first 
prototype because they indicate big effort for producing workload """

RISKY_MODULES = {
    "requests", "urllib", "http", "socket", "sqlite3", "subprocess",
    "shutil", "smtplib", "ftplib", "psycopg2", "pymongo", "redis",
    "os", "pathlib", "tempfile",
}

""" This words indicates that the function would not be scanned for the first 
prototype because they indicate big effort for producing workload """
RISKY_CALLS = {"open", "input", "exec", "eval", "invoke"}

""" This words indicates that the function would not be scanned for the first 
prototype because they indicate big effort for producing workload """
RISKY_ATTRS = {"read_text", "write_text", "read_bytes", "write_bytes", "unlink", "mkdir"}


@dataclass
class FilterResult:
    runnable: bool
    skip_reason: str | None = None


def _find_side_effect(source: str) -> str | None:
    """Walk the function's AST and return a description of the first side effect, or None."""
    # The source is a single function; callers must dedent it first (needed for methods).
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Builtin calls such as open() or input()
            if isinstance(func, ast.Name) and func.id in RISKY_CALLS:
                return f"calls {func.id}()"
            if isinstance(func, ast.Attribute):
                # I/O-style methods such as path.read_text()
                if func.attr in RISKY_ATTRS:
                    return f"calls .{func.attr}()"
                # Calls on known risky modules such as requests.get()
                if isinstance(func.value, ast.Name) and func.value.id in RISKY_MODULES:
                    return f"uses module {func.value.id}"
        # Modifying global or nonlocal state
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return "modifies global/nonlocal state"
    return None

def check_function(func: FunctionInfo) -> FilterResult:
    if func.is_async:
        return FilterResult(False, "async function")
    if func.is_method:
        return FilterResult(False, "method (classes not supported yet)")

    try:
        reason = _find_side_effect(_dedent(func.source))
    except SyntaxError:
        return FilterResult(False, "source could not be parsed")

    if reason:
        return FilterResult(False, f"side effect: {reason}")
    return FilterResult(True)


def _dedent(source: str) -> str:
    import textwrap
    return textwrap.dedent(source)


def filter_functions(funcs: list[FunctionInfo]) -> tuple[list[FunctionInfo], list[tuple[FunctionInfo, str]]]:
    """Return (runnable functions, [(skipped function, reason)])."""
    runnable, skipped = [], []
    for f in funcs:
        result = check_function(f)
        if result.runnable:
            runnable.append(f)
        else:
            skipped.append((f, result.skip_reason))
    return runnable, skipped


if __name__ == "__main__":
    import sys
    from extractor import extract_functions

    runnable, skipped = filter_functions(extract_functions(sys.argv[1]))
    print(f"Runnable: {len(runnable)} | Skipped: {len(skipped)}")
    for f, reason in skipped:
        print(f"  SKIP {f.qualified_name}: {reason}")
    for f in runnable:
        print(f"  RUN {f.qualified_name}")