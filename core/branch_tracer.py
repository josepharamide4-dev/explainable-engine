import ast
import inspect

from reporting.models import AnalysisReport


class BranchTracer(ast.NodeVisitor):
    def __init__(self, variable_details=None):
        self.variable_details = variable_details or {}
        self.branch_trace = []

    def visit_If(self, node):
        condition_text = self._to_source(node.test)
        evaluation = self._evaluate_condition(node.test)

        if evaluation is True:
            self.branch_trace.append(
                f"Line {node.lineno}: condition `{condition_text}` evaluated to True, so the `if` branch ran."
            )
        elif evaluation is False:
            if node.orelse:
                self.branch_trace.append(
                    f"Line {node.lineno}: condition `{condition_text}` evaluated to False, so the `else` branch ran."
                )
            else:
                self.branch_trace.append(
                    f"Line {node.lineno}: condition `{condition_text}` evaluated to False, so the guarded block was skipped."
                )
        else:
            self.branch_trace.append(
                f"Line {node.lineno}: condition `{condition_text}` could not be evaluated from the available runtime values."
            )

        self.generic_visit(node)

    def _to_source(self, node):
        if hasattr(ast, "unparse"):
            return ast.unparse(node)
        return "<condition>"

    def _evaluate_condition(self, node):
        if isinstance(node, ast.Name):
            if node.id in self.variable_details:
                return bool(self.variable_details[node.id])
            return None

        if isinstance(node, ast.Constant):
            return bool(node.value)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = self._evaluate_condition(node.operand)
            if value is None:
                return None
            return not value

        if isinstance(node, ast.Compare):
            left = self._resolve_value(node.left)
            if len(node.ops) != 1 or len(node.comparators) != 1:
                return None

            right = self._resolve_value(node.comparators[0])
            if left is None or right is None:
                return None

            op = node.ops[0]

            try:
                if isinstance(op, ast.Is):
                    return left is right
                if isinstance(op, ast.IsNot):
                    return left is not right
                if isinstance(op, ast.Eq):
                    return left == right
                if isinstance(op, ast.NotEq):
                    return left != right
                if isinstance(op, ast.Lt):
                    return left < right
                if isinstance(op, ast.LtE):
                    return left <= right
                if isinstance(op, ast.Gt):
                    return left > right
                if isinstance(op, ast.GtE):
                    return left >= right
            except Exception:
                return None

        if isinstance(node, ast.BoolOp):
            values = [self._evaluate_condition(v) for v in node.values]
            if any(v is None for v in values):
                return None

            if isinstance(node.op, ast.And):
                return all(values)

            if isinstance(node.op, ast.Or):
                return any(values)

        return None

    def _resolve_value(self, node):
        if isinstance(node, ast.Name):
            return self.variable_details.get(node.id)

        if isinstance(node, ast.Constant):
            return node.value

        return None


def trace_branches(report: AnalysisReport, func, variable_details=None) -> AnalysisReport:
    variable_details = variable_details or {}

    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
    except Exception as exc:
        report.notes.append(f"Branch tracing failed: {type(exc).__name__}: {exc}")
        return report

    tracer = BranchTracer(variable_details=variable_details)
    tracer.visit(tree)

    report.branch_trace = tracer.branch_trace

    if tracer.branch_trace:
        report.notes.append("Branch trace generated from function conditions and runtime values.")

    return report