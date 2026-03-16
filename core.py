from core.explainer import explain_error
from reporting.formatter import format_report


def safe_explain(func, variable_details=None):
    try:
        func()
    except Exception as exc:
        report = explain_error(
            error_type=type(exc).__name__,
            error_message=str(exc),
            function_name=func.__name__,
            variable_details=variable_details or {},
        )

        print(format_report(report))