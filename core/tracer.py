import ast
import inspect

from reporting.models import AnalysisReport


class AssignmentTracer(ast.NodeVisitor):
    def __init__(self):
        self.assignments = {}

    def visit_Assign(self, node):
        value_text = ast.unparse(node.value) if hasattr(ast, "unparse") else "<expression>"

        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments[target.id] = (
                    node.lineno,
                    value_text,
                )

        self.generic_visit(node)


def trace_variables(report: AnalysisReport, func, variable_details=None) -> AnalysisReport:
    variable_details = variable_details or {}

    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
    except Exception as exc:
        report.notes.append(f"Root cause tracing failed: {type(exc).__name__}: {exc}")
        return report

    tracer = AssignmentTracer()
    tracer.visit(tree)

    trace_lines = []

    for name in variable_details.keys():
        if name in tracer.assignments:
            lineno, assigned_value = tracer.assignments[name]
            trace_lines.append(
                f"Variable `{name}` was last assigned on line {lineno} as: {assigned_value}"
            )
        else:
            trace_lines.append(
                f"Variable `{name}` was provided at runtime but no local assignment was found in the function source."
            )

    report.root_cause_trace = trace_lines

    if trace_lines:
        report.notes.append("Root cause trace generated from local variable assignments.")

    return report