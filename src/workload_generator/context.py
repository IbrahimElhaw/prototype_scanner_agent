import ast
import textwrap
from extractor import ClassInfo, FunctionInfo


def referenced_classes(func: FunctionInfo, classes: dict[str, ClassInfo]) -> list[ClassInfo]:
    """Return project classes that appear in the signature or anywhere in the body."""
    tree = ast.parse(textwrap.dedent(func.source))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return [classes[name] for name in names if name in classes]

def helper_catalog(target: FunctionInfo, runnable: list[FunctionInfo], limit: int = 30) -> list[FunctionInfo]:
    """Project functions the builder may call to create its inputs.
    We exclude the target itself, methods, and functions that return None."""

    """Why: for structured text inputs, the format is often not visible
    in the target's source and the LLM would guess it. Calling a project function
    that already produces the format avoids that. We exclude the target itself,
    methods, and functions returning None. We do NOT filter by return type yet
    (deferred until it causes a real problem).
    """

    helpers = []
    for func in runnable:
        if func.qualified_name == target.qualified_name or func.is_method:
            continue
        if func.signature.endswith("-> None"):
            continue
        helpers.append(func)
    return helpers[:limit]