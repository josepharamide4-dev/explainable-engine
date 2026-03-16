import linecache
import traceback

from core.branch_tracer import trace_branches
from core.call_tracer import trace_function_calls
from core.explainer import explain_error
from core.inspector import inspect_function
from core.tracer import trace_variables
from reporting.exporter import export_report_json, export_report_text
from reporting.formatter import format_report


def analyze_function(
    func,
    variable_details=None,
    related_functions=None,
    export_text_path=None,
    export_json_path=None,
    print_report=True,
):
    try:
        func()
    except Exception as exc:
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1]

        report = explain_error(
            error_type=type(exc).__name__,
            error_message=str(exc),
            function_name=func.__name__,
            variable_details=variable_details or {},
        )

        report.file_name = last.filename
        report.line_number = last.lineno
        report.code_line = linecache.getline(last.filename, last.lineno).strip()

        report = inspect_function(report, func)
        report = trace_variables(report, func, variable_details or {})
        report = trace_function_calls(
            report,
            func,
            related_functions=related_functions or [],
            variable_details=variable_details or {},
        )
        report = trace_branches(report, func, variable_details or {})

        if print_report:
            print(format_report(report))

        if export_text_path:
            export_report_text(report, export_text_path)

        if export_json_path:
            export_report_json(report, export_json_path)

        return report

    return None