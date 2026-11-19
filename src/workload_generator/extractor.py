import ast
from dataclasses import dataclass
from pathlib import Path

# These DIRs will not be scanned
EXCLUDED_DIRS = {
    ".venv", "venv", "__pycache__", ".git", "build", "dist",
    "node_modules", "tests", "test",
}

@dataclass
class FunctionInfo:
    qualified_name: str      # example: "pkg.utils:Parser.parse"
    file_path: str
    lineno: int
    signature: str           # example: "(self, data: list[int], k=3) -> int"
    docstring: str | None
    source: str
    is_method: bool         # TODO, class methods will be later excluded from investigation in the prototype
    is_async: bool


@dataclass
class ClassInfo:
    name: str
    module: str          # e.g. "shop_analytics.models"
    source: str


def _is_test_file(file: Path) -> bool:
    name = file.name
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"

def _module_name(file: Path, root: Path) -> str:
    "pkg/utils.py → 'pkg.utils', and pkg/init.py → 'pkg'."
    parts = list(file.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    # returns as example (orders: list[Order]) -> list[tuple[int, int]]
    sig = f"({ast.unparse(node.args)})"
    if node.returns is not None:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _collect(body, class_stack, module, file, source, out):
    """Iterates over the members of a module or class.
     Does not descend into functions (nested functions cannot be imported)."""

    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = ".".join(class_stack + [node.name])
            out.append(FunctionInfo(
                qualified_name=f"{module}:{qualname}",
                file_path=str(file),
                lineno=node.lineno,
                signature=_build_signature(node),
                docstring=ast.get_docstring(node),
                source=ast.get_source_segment(source, node) or "",
                is_method=bool(class_stack),
                is_async=isinstance(node, ast.AsyncFunctionDef),
            ))
        elif isinstance(node, ast.ClassDef):
            _collect(node.body, class_stack + [node.name], module, file, source, out)


def extract_functions(project_root: str) -> list[FunctionInfo]:
    root = Path(project_root).resolve()
    result: list[FunctionInfo] = []

    for file in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in file.relative_to(root).parts) or  _is_test_file(file):
            continue
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            print(f"extract_functions in extractor skipped {file}, cannot be read")
            continue

        _collect(tree.body, [], _module_name(file, root), file, source, result)

    return result


def extract_classes(project_root: str) -> dict[str, ClassInfo]:
    """Map class name -> ClassInfo for every top-level class in the project.
    If two classes share a name, the last one found wins (acceptable for the prototype)."""
    root = Path(project_root).resolve()
    classes: dict[str, ClassInfo] = {}

    for file in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in file.relative_to(root).parts):
            continue
        if _is_test_file(file):
            continue
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        module = _module_name(file, root)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = ClassInfo(
                    name=node.name,
                    module=module,
                    source=ast.get_source_segment(source, node) or "",
                )
    return classes

if __name__ == "__main__":
    import sys
    funcs = extract_functions(sys.argv[1])
    print(f"Found {len(funcs)} functions")
    for f in funcs:
        print(f.qualified_name, f.signature)
    classes = extract_classes(sys.argv[1])
    print(classes)