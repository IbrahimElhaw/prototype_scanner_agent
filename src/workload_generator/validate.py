import ast
import builtins

# Names the builder may use without defining them (everything else must be local or known)
ALLOWED_GLOBALS = {"random"}


class _StripImports(ast.NodeTransformer):
    """Remove every import statement; we add the correct imports ourselves."""

    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None


def normalize(code: str) -> str:
    """Drop all imports (top-level and inside the builder) and all comments.
    Raises SyntaxError if the code cannot be parsed."""
    tree = _StripImports().visit(ast.parse(code))
    return ast.unparse(ast.fix_missing_locations(tree))


def validate_builder(code: str, name: str, target_name: str, known_names: set[str]) -> str | None:
    """Return an error message if the builder is malformed, else None.
    `code` must already be normalized. `known_names` are the classes and helper
    functions that we import for the builder."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"syntax error: {e}"

    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(funcs) != 1 or funcs[0].name != name:
        return f"the code must contain exactly one function named {name} and nothing else at module level"
    func = funcs[0]
    if [a.arg for a in func.args.args] != ["n"]:
        return "the builder must take exactly one parameter named n"

    # Names defined inside the builder: parameters, assignments, loop and comprehension variables
    defined = set()
    for node in ast.walk(func):
        if isinstance(node, ast.arg):
            defined.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
        elif isinstance(node, ast.FunctionDef) and node is not func:
            defined.add(node.name)

    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            return "try/except is not allowed in a builder"
        if isinstance(node, ast.Return):
            if not (isinstance(node.value, ast.Tuple) and len(node.value.elts) == 2):
                return "return must be a 2-tuple: (args_tuple, kwargs_dict)"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == target_name:
            return f"the builder must not call the target function {target_name}"
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if (node.id not in defined and node.id not in known_names
                    and node.id not in ALLOWED_GLOBALS and not hasattr(builtins, node.id)):
                return f"undefined name: {node.id}"
    return None