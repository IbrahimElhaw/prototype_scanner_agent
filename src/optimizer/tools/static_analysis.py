import ast

from radon.complexity import cc_visit

from optimizer.config import Config
from optimizer.state import StaticRow

_LOOP_NODES = (ast.For, ast.AsyncFor, ast.While)


class _MaxLoopDepth(ast.NodeVisitor):
    """Tracks the deepest loop nesting inside one function body."""

    def __init__(self) -> None:
        self.depth = 0
        self.max_depth = 0

    def _enter(self, node: ast.AST, levels: int = 1) -> None:
        self.depth += levels
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= levels

    def visit_For(self, node: ast.AST) -> None:
        self._enter(node)

    visit_AsyncFor = visit_While = visit_For

    def visit_comprehension_node(self, node: ast.AST) -> None:
        # every "for" clause inside a comprehension is one loop level
        self._enter(node, levels=len(node.generators))

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_comprehension_node

    def visit_FunctionDef(self, node: ast.AST) -> None:
        pass  # nested functions are analyzed as separate rows

    visit_AsyncFunctionDef = visit_FunctionDef


def _detect_patterns(func: ast.AST) -> list[str]:
    patterns: list[str] = []

    visitor = _MaxLoopDepth()
    for stmt in func.body:  # visit the body only, not the function node itself
        visitor.visit(stmt)
    if visitor.max_depth >= 2:
        patterns.append("nested_loop")

    return patterns


def analyze_package(config: Config) -> list[StaticRow]:
    """Return one StaticRow per function found in the target package."""
    package_dir = config.package_dir.resolve()
    rows: list[StaticRow] = []

    for path in sorted(package_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        rel_file = path.relative_to(package_dir).as_posix()

        # radon complexity, keyed by (function name, line number)
        complexity = {(b.name, b.lineno): b.complexity for b in cc_visit(source)}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                rows.append(
                    StaticRow(
                        file=rel_file,
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno,
                        complexity=complexity.get((node.name, node.lineno), 1),
                        patterns=_detect_patterns(node)
                    )
                )

    return rows
