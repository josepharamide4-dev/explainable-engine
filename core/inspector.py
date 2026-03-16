import ast
import inspect

from reporting.models import AnalysisReport


class CodeInspector(ast.NodeVisitor):

    def __init__(self):
        self.findings = []
        self.bug_risks = []

    # Detect nested loops
    def visit_For(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child is not node:
                self.findings.append(
                    f"Line {node.lineno}: Nested loop detected — possible O(n²) complexity."
                )
        self.generic_visit(node)

    # Detect append in loops
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "append":
                self.findings.append(
                    f"Line {node.lineno}: List append detected — consider list comprehension."
                )
        self.generic_visit(node)

    # Detect unsafe dictionary access
    def visit_Subscript(self, node):

        if isinstance(node.value, ast.Name):
            self.bug_risks.append(
                f"Line {node.lineno}: Direct dictionary key access may raise KeyError."
            )

        self.generic_visit(node)

    # Detect mutable defaults
    def visit_FunctionDef(self, node):

        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict)):
                self.bug_risks.append(
                    f"Line {node.lineno}: Mutable default argument detected."
                )

        self.generic_visit(node)


def inspect_function(report: AnalysisReport, func):

    source = inspect.getsource(func)

    tree = ast.parse(source)

    inspector = CodeInspector()

    inspector.visit(tree)

    report.inspection_findings = inspector.findings
    report.bug_risks = inspector.bug_risks

    if inspector.findings:
        report.optimization_status = "potential inefficiencies detected"

    if inspector.bug_risks:
        report.notes.append("Potential bug risks detected.")

    return report