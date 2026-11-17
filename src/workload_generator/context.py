import ast
from extractor import ClassInfo, FunctionInfo


def referenced_classes(func: FunctionInfo, classes: dict[str, ClassInfo]) -> list[ClassInfo]:
    """Return project classes whose names appear in the function's signature.
    We look at the signature only, because the types the caller must build are declared there."""
    tree = ast.parse(f"def f{func.signature.split(' -> ')[0]}: pass")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return [classes[name] for name in names if name in classes]


def helper_catalog(target: FunctionInfo, runnable: list[FunctionInfo], limit: int = 30) -> list[FunctionInfo]:
    """Project functions the builder may call to create its inputs.
    We exclude the target itself, methods, and functions that return None."""
    helpers = []
    for func in runnable:
        if func.qualified_name == target.qualified_name or func.is_method:
            continue
        if func.signature.endswith("-> None"):
            continue
        helpers.append(func)
    return helpers[:limit]