import ast
import inspect
import importlib.util
from pathlib import Path

from config.settings import load_settings
from reporting.models import AnalysisReport


def load_module_from_file(file_path: Path):
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def find_safe_functions(module, file_path: Path):
    functions = []

    members = inspect.getmembers(module)
    for name, obj in members:
        if not inspect.isfunction(obj):
            continue

        try:
            sig = inspect.signature(obj)
        except (TypeError, ValueError):
            continue

        required_params = [
            parameter
            for parameter in sig.parameters.values()
            if parameter.default is parameter.empty
            and parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        try:
            line_number = inspect.getsourcelines(obj)[1]
        except (OSError, TypeError):
            line_number = 0

        functions.append(
            {
                "name": name,
                "required_params": len(required_params),
                "file_name": inspect.getsourcefile(obj) or str(file_path),
                "line_number": line_number,
                "doc": inspect.getdoc(obj) or "",
                "source_obj": obj,
            }
        )

    return functions


def _count_nodes(tree, node_type):
    return sum(isinstance(node, node_type) for node in ast.walk(tree))


def _safe_parse_function_source(obj):
    try:
        source = inspect.getsource(obj)
        return source, ast.parse(source), None
    except Exception as exc:
        return None, None, exc


def _collect_structure_counts(tree):
    return {
        "for_count": _count_nodes(tree, ast.For),
        "while_count": _count_nodes(tree, ast.While),
        "if_count": _count_nodes(tree, ast.If),
        "call_count": _count_nodes(tree, ast.Call),
        "return_count": _count_nodes(tree, ast.Return),
    }


def build_trace_report(func_info) -> AnalysisReport:
    obj = func_info["source_obj"]

    report = AnalysisReport(
        title=f"Trace preview for function `{func_info['name']}`",
        problem_type="RuntimeTracePreview",
        severity="info",
        explanation=(
            "This trace command is running in safe preview mode. "
            "It inspects the function structure without executing it."
        ),
        suspected_cause=(
            "Execution was intentionally skipped to avoid hangs, infinite loops, "
            "and side effects during project-wide tracing."
        ),
        confidence="high",
        suggested_next_action=(
            "Review this function manually or use analyze-file if you want real runtime analysis."
        ),
    )

    report.file_name = func_info["file_name"]
    report.line_number = func_info["line_number"]
    report.code_line = f"def {func_info['name']}(...)"

    report.observed_facts.extend(
        [
            f"Function name: {func_info['name']}",
            f"Required parameters: {func_info['required_params']}",
        ]
    )

    if func_info["doc"]:
        report.notes.append(f"Docstring: {func_info['doc']}")

    source, tree, parse_error = _safe_parse_function_source(obj)

    if parse_error is not None:
        report.notes.append(
            f"Could not inspect source structure: {type(parse_error).__name__}: {parse_error}"
        )
        return report

    counts = _collect_structure_counts(tree)

    report.observed_facts.extend(
        [
            f"For-loops found: {counts['for_count']}",
            f"While-loops found: {counts['while_count']}",
            f"If-branches found: {counts['if_count']}",
            f"Function calls found: {counts['call_count']}",
            f"Return statements found: {counts['return_count']}",
        ]
    )

    if counts["while_count"] > 0:
        report.bug_risks.append(
            "Contains a while-loop. Review manually for termination conditions."
        )

    if func_info["required_params"] > 0:
        report.bug_risks.append(
            "Requires input arguments, so it was not eligible for automatic execution."
        )

    if counts["for_count"] >= 2:
        report.inspection_findings.append(
            "Multiple for-loops detected. Review for possible nested-loop inefficiency."
        )

    if counts["while_count"] > 0 or counts["for_count"] >= 2:
        report.optimization_status = "manual review recommended"
        report.optimization_notes.append(
            "This function contains loop structures that may deserve closer inspection."
        )
    else:
        report.optimization_status = "no obvious high-risk execution pattern detected"

    return report


def scan_runtime(project_path, config_path: str = "explainable.toml"):
    settings = load_settings(config_path)
    ignore_names = set(settings["scan"]["ignore"])

    base = Path(project_path)
    reports = []

    python_files = [
        file_path
        for file_path in base.rglob("*.py")
        if not any(part in ignore_names for part in file_path.parts)
    ]

    for file_path in python_files:
        module = load_module_from_file(file_path)
        if module is None:
            continue

        functions = find_safe_functions(module, file_path)
        reports.extend(build_trace_report(func_info) for func_info in functions)

    return reports