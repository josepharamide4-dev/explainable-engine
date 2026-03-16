import ast
from pathlib import Path


class CallGraphVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_function = None
        self.graph = {}

    def visit_FunctionDef(self, node):
        self.current_function = node.name

        if self.current_function not in self.graph:
            self.graph[self.current_function] = set()

        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node):
        if self.current_function is None:
            return

        if isinstance(node.func, ast.Name):
            called = node.func.id
            self.graph[self.current_function].add(called)

        self.generic_visit(node)


def build_call_graph(file_path):
    path = Path(file_path)

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return {}

    visitor = CallGraphVisitor()
    visitor.visit(tree)

    return visitor.graph