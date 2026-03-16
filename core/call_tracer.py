import ast
import inspect

from reporting.models import AnalysisReport


class CallAssignmentTracer(ast.NodeVisitor):
    def __init__(self):
        self.call_assignments = []
        self.return_values = {}

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            call_name = self._get_call_name(node.value)

            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.call_assignments.append(
                        {
                            "variable": target.id,
                            "line": node.lineno,
                            "call_name": call_name,
                        }
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        function_name = node.name
        return_value = None

        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                if hasattr(ast, "unparse"):
                    return_value = ast.unparse(child.value)
                else:
                    return_value = "<return expression>"

        self.return_values[function_name] = return_value
        self.generic_visit(node)

    def _get_call_name(self, call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id

        if isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr

        return "<unknown call>"
        

def trace_function_calls(report: AnalysisReport, func, related_functions=None, variable_details=None) -> AnalysisReport:
    variable_details = variable_details or {}
    related_functions = related_functions or []

    try:
        main_source = inspect.getsource(func)
        main_tree = ast.parse(main_source)
    except Exception as exc:
        report.notes.append(f"Call tracing failed for main function: {type(exc).__name__}: {exc}")
        return report

    main_tracer = CallAssignmentTracer()
    main_tracer.visit(main_tree)

    related_return_values = {}

    for related_func in related_functions:
        try:
            source = inspect.getsource(related_func)
            tree = ast.parse(source)
            tracer = CallAssignmentTracer()
            tracer.visit(tree)
            related_return_values.update(tracer.return_values)
        except Exception as exc:
            report.notes.append(
                f"Call tracing skipped for related function `{related_func.__name__}`: {type(exc).__name__}: {exc}"
            )

    call_trace_lines = []

    for entry in main_tracer.call_assignments:
        variable_name = entry["variable"]
        call_name = entry["call_name"]
        line = entry["line"]

        if variable_name in variable_details:
            runtime_value = variable_details[variable_name]
            trace_line = (
                f"Variable `{variable_name}` was assigned from call `{call_name}()` on line {line} "
                f"and had runtime value {runtime_value!r}"
            )

            if call_name in related_return_values and related_return_values[call_name] is not None:
                trace_line += f"; `{call_name}()` appears to return: {related_return_values[call_name]}"

            call_trace_lines.append(trace_line)

    report.call_trace = call_trace_lines

    if call_trace_lines:
        report.notes.append("Function call trace generated from local call assignments.")

    return report