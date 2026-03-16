import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from config.settings import load_settings
from core.bug_chain import find_bug_chains
from core.call_graph import build_call_graph
from core.file_loader import (
    get_function_from_module,
    get_zero_arg_functions,
    load_module_from_file,
)
from core.logger import setup_logger
from core.runner import analyze_function
from core.runtime_scanner import scan_runtime
from core.scanner import scan_project, scan_python_file
from reporting.exporter import (
    export_reports_json,
    export_reports_text,
)
from reporting.formatter import format_report


EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 1
EXIT_ANALYSIS_FOUND = 2
EXIT_INTERNAL_ERROR = 3

SEVERITY_RANK = {
    "": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def run_cli():
    parser = argparse.ArgumentParser(
        description="Explainable - Python debugging and optimization assistant"
    )

    parser.add_argument(
        "--config",
        default="explainable.toml",
        help="Path to the Explainable configuration file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console logging except for command output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging to the console",
    )

    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan a project for potential issues")
    scan_parser.add_argument("path")
    scan_parser.add_argument("--text", dest="text_output")
    scan_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")

    trace_parser = subparsers.add_parser(
        "trace",
        help="Safely preview functions across a project without executing them"
    )
    trace_parser.add_argument("path")
    trace_parser.add_argument("--text", dest="text_output")
    trace_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")

    analyze_file_parser = subparsers.add_parser(
        "analyze-file",
        help="Analyze a real function from a real Python file"
    )
    analyze_file_parser.add_argument("file_path")
    analyze_file_parser.add_argument("--function", required=True, dest="function_name")
    analyze_file_parser.add_argument("--text", dest="text_output")
    analyze_file_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")

    list_functions_parser = subparsers.add_parser(
        "list-functions",
        help="List zero-argument functions in a Python file"
    )
    list_functions_parser.add_argument("file_path")
    list_functions_parser.add_argument("--json", action="store_true", dest="json_mode")

    call_graph_parser = subparsers.add_parser(
        "call-graph",
        help="Build a function call graph for a Python file"
    )
    call_graph_parser.add_argument("file_path")
    call_graph_parser.add_argument("--json", action="store_true", dest="json_mode")

    bug_chain_parser = subparsers.add_parser(
        "bug-chain",
        help="Trace likely caller chains leading to a target function"
    )
    bug_chain_parser.add_argument("file_path")
    bug_chain_parser.add_argument("--function", required=True, dest="function_name")
    bug_chain_parser.add_argument("--json", action="store_true", dest="json_mode")

    perf_parser = subparsers.add_parser(
        "perf",
        help="Analyze a Python file for performance-related heuristics"
    )
    perf_parser.add_argument("file_path")
    perf_parser.add_argument("--json", action="store_true", dest="json_mode")
    perf_parser.add_argument(
        "--fail-on",
        choices=["low", "medium", "high"],
        dest="fail_on",
        help="Return analysis exit code only if findings meet or exceed this severity threshold",
    )
    perf_parser.add_argument(
        "--fail-count",
        type=int,
        dest="fail_count",
        help="Return analysis exit code only if at least this many findings meet the threshold",
    )

    perf_summary_parser = subparsers.add_parser(
        "perf-summary",
        help="Aggregate performance findings across a whole project"
    )
    perf_summary_parser.add_argument("path")
    perf_summary_parser.add_argument("--json", action="store_true", dest="json_mode")
    perf_summary_parser.add_argument(
        "--fail-on",
        choices=["low", "medium", "high"],
        dest="fail_on",
        help="Return analysis exit code only if findings meet or exceed this severity threshold",
    )
    perf_summary_parser.add_argument(
        "--fail-count",
        type=int,
        dest="fail_count",
        help="Return analysis exit code only if at least this many findings meet the threshold",
    )
    perf_summary_parser.add_argument(
        "--top",
        type=int,
        default=10,
        dest="top",
        help="Maximum number of files to show in the summary",
    )
    perf_summary_parser.add_argument(
        "--sort-by",
        choices=["severity", "findings", "file"],
        default="severity",
        dest="sort_by",
        help="How to sort files in the summary",
    )

    perf_compare_parser = subparsers.add_parser(
        "perf-compare",
        help="Compare current performance summary against a saved JSON baseline"
    )
    perf_compare_parser.add_argument("path")
    perf_compare_parser.add_argument("--baseline", required=True, dest="baseline_path")
    perf_compare_parser.add_argument("--text", dest="text_output")
    perf_compare_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")
    perf_compare_parser.add_argument(
        "--top",
        type=int,
        default=10,
        dest="top",
        help="Maximum number of files to include in the generated summary before comparison",
    )
    perf_compare_parser.add_argument(
        "--sort-by",
        choices=["severity", "findings", "file"],
        default="severity",
        dest="sort_by",
        help="How to sort files in the generated summary before comparison",
    )

    args = parser.parse_args()

    if args.quiet and args.verbose:
        print("Error: --quiet and --verbose cannot be used together.")
        return EXIT_INPUT_ERROR

    if hasattr(args, "fail_count") and args.fail_count is not None and args.fail_count < 1:
        print("Error: --fail-count must be at least 1.")
        return EXIT_INPUT_ERROR

    if hasattr(args, "top") and args.top is not None and args.top < 1:
        print("Error: --top must be at least 1.")
        return EXIT_INPUT_ERROR

    console_level = logging.INFO
    if args.quiet:
        console_level = logging.CRITICAL + 1
    elif args.verbose:
        console_level = logging.DEBUG

    logger = setup_logger(console_level=console_level)

    if not args.command:
        parser.print_help()
        return EXIT_INPUT_ERROR

    logger.info("Explainable CLI started")
    logger.info("Command received: %s", args.command)
    logger.debug("Parsed arguments: %s", args)

    try:
        settings = load_settings(args.config)
        logger.info("Loaded configuration from: %s", args.config)
        logger.debug("Resolved settings: %s", settings)

        if args.command == "scan":
            return run_scan(logger, args.path, args.text_output, args.json_output, settings, args.config)

        if args.command == "trace":
            return run_trace(logger, args.path, args.text_output, args.json_output, settings, args.config)

        if args.command == "analyze-file":
            return run_analyze_file(
                logger,
                args.file_path,
                args.function_name,
                args.text_output,
                args.json_output,
                settings,
            )

        if args.command == "list-functions":
            return run_list_functions(logger, args.file_path, args.json_mode)

        if args.command == "call-graph":
            return run_call_graph(logger, args.file_path, args.json_mode)

        if args.command == "bug-chain":
            return run_bug_chain(logger, args.file_path, args.function_name, args.json_mode)

        if args.command == "perf":
            return run_perf(logger, args.file_path, args.json_mode, args.fail_on, args.fail_count)

        if args.command == "perf-summary":
            return run_perf_summary(
                logger,
                args.path,
                args.json_mode,
                args.config,
                args.fail_on,
                args.fail_count,
                args.top,
                args.sort_by,
            )

        if args.command == "perf-compare":
            return run_perf_compare(
                logger,
                args.path,
                args.baseline_path,
                args.text_output,
                args.json_output,
                args.config,
                args.top,
                args.sort_by,
            )

        parser.print_help()
        return EXIT_INPUT_ERROR

    except Exception as exc:
        logger.exception("Internal CLI failure")
        print(f"Internal error: {type(exc).__name__}: {exc}")
        return EXIT_INTERNAL_ERROR


def choose_default_export_path(command_name: str, extension: str) -> str:
    return f"{command_name}_report.{extension}"


def count_findings_at_or_above_threshold(scored_findings, fail_on: str | None) -> int:
    threshold = fail_on or "low"
    threshold_rank = SEVERITY_RANK[threshold]

    count = 0
    for item in scored_findings:
        severity = item.get("severity", "")
        if SEVERITY_RANK.get(severity, 0) >= threshold_rank:
            count += 1
    return count


def threshold_triggered_from_findings(scored_findings, fail_on: str | None, fail_count: int | None) -> bool:
    qualifying_count = count_findings_at_or_above_threshold(scored_findings, fail_on)

    if fail_count is not None:
        return qualifying_count >= fail_count

    return qualifying_count > 0


def sort_reports_for_perf_summary(reports, sort_by: str):
    if sort_by == "file":
        return sorted(reports, key=lambda r: r.file_name.lower())

    if sort_by == "findings":
        return sorted(
            reports,
            key=lambda r: (
                len(r.performance_scored_findings),
                SEVERITY_RANK.get(r.performance_overall_severity, 0),
                r.file_name.lower(),
            ),
            reverse=True,
        )

    return sorted(
        reports,
        key=lambda r: (
            SEVERITY_RANK.get(r.performance_overall_severity, 0),
            len(r.performance_scored_findings),
            r.file_name.lower(),
        ),
        reverse=True,
    )


def build_perf_summary_payload(path, config_path="explainable.toml", fail_on=None, fail_count=None, top=10, sort_by="severity"):
    reports = scan_project(path, config_path=config_path)

    total_files = len(reports)
    files_with_findings = [r for r in reports if r.performance_scored_findings]
    total_files_with_findings = len(files_with_findings)

    totals = {"high": 0, "medium": 0, "low": 0}
    all_scored_findings = []

    for report in reports:
        summary = report.performance_severity_summary or {}
        totals["high"] += summary.get("high", 0)
        totals["medium"] += summary.get("medium", 0)
        totals["low"] += summary.get("low", 0)
        all_scored_findings.extend(report.performance_scored_findings)

    ranked_files = sort_reports_for_perf_summary(reports, sort_by)

    top_files = []
    for report in ranked_files[:top]:
        top_files.append(
            {
                "file_name": report.file_name,
                "overall_severity": report.performance_overall_severity,
                "finding_count": len(report.performance_scored_findings),
                "severity_summary": report.performance_severity_summary,
            }
        )

    highest_found = ""
    for report in reports:
        sev = report.performance_overall_severity or ""
        if SEVERITY_RANK.get(sev, 0) > SEVERITY_RANK.get(highest_found, 0):
            highest_found = sev

    qualifying_count = count_findings_at_or_above_threshold(all_scored_findings, fail_on)
    triggered = threshold_triggered_from_findings(all_scored_findings, fail_on, fail_count)

    return {
        "path": path,
        "fail_on": fail_on,
        "fail_count": fail_count,
        "sort_by": sort_by,
        "top": top,
        "qualifying_finding_count": qualifying_count,
        "threshold_triggered": triggered,
        "highest_severity_found": highest_found,
        "total_files_scanned": total_files,
        "files_with_findings": total_files_with_findings,
        "total_severity_summary": totals,
        "top_files": top_files,
    }


def load_json_file(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compare_perf_summaries(current: dict, baseline: dict) -> dict:
    current_totals = current.get("total_severity_summary", {})
    baseline_totals = baseline.get("total_severity_summary", {})

    severity_delta = {
        "high": current_totals.get("high", 0) - baseline_totals.get("high", 0),
        "medium": current_totals.get("medium", 0) - baseline_totals.get("medium", 0),
        "low": current_totals.get("low", 0) - baseline_totals.get("low", 0),
    }

    current_files = {item["file_name"]: item for item in current.get("top_files", [])}
    baseline_files = {item["file_name"]: item for item in baseline.get("top_files", [])}

    new_files_in_top = sorted([name for name in current_files if name not in baseline_files])
    removed_files_from_top = sorted([name for name in baseline_files if name not in current_files])

    finding_count_delta = (
        current.get("qualifying_finding_count", 0) - baseline.get("qualifying_finding_count", 0)
    )

    total_files_with_findings_delta = (
        current.get("files_with_findings", 0) - baseline.get("files_with_findings", 0)
    )

    regression_detected = (
        severity_delta["high"] > 0
        or severity_delta["medium"] > 0
        or severity_delta["low"] > 0
        or finding_count_delta > 0
        or total_files_with_findings_delta > 0
    )

    return {
        "baseline_path": baseline.get("path", ""),
        "current_path": current.get("path", ""),
        "regression_detected": regression_detected,
        "finding_count_delta": finding_count_delta,
        "files_with_findings_delta": total_files_with_findings_delta,
        "severity_delta": severity_delta,
        "new_files_in_top": new_files_in_top,
        "removed_files_from_top": removed_files_from_top,
        "current": current,
        "baseline": baseline,
    }


def write_text_file(output_path: str, content: str):
    Path(output_path).write_text(content, encoding="utf-8")


def write_json_file(output_path: str, payload: dict):
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_perf_compare_text(comparison: dict) -> str:
    lines = [
        "Performance Baseline Comparison:",
        "",
        f"Current path: {comparison['current_path']}",
        f"Baseline path: {comparison['baseline_path']}",
        f"Regression detected: {comparison['regression_detected']}",
        f"Finding count delta: {comparison['finding_count_delta']}",
        f"Files with findings delta: {comparison['files_with_findings_delta']}",
    ]

    severity_delta = comparison["severity_delta"]
    lines.append(
        "Severity delta: "
        f"high={severity_delta['high']}, "
        f"medium={severity_delta['medium']}, "
        f"low={severity_delta['low']}"
    )

    lines.extend(["", "New files in top list:"])
    if comparison["new_files_in_top"]:
        for item in comparison["new_files_in_top"]:
            lines.append(f"- {item}")
    else:
        lines.append("(none)")

    lines.extend(["", "Removed files from top list:"])
    if comparison["removed_files_from_top"]:
        for item in comparison["removed_files_from_top"]:
            lines.append(f"- {item}")
    else:
        lines.append("(none)")

    return "\n".join(lines)


def run_scan(logger, path, text_output=None, json_output=None, settings=None, config_path="explainable.toml"):
    logger.info("Scanning project: %s", path)

    reports = scan_project(path, config_path=config_path)
    logger.info("Scan completed with %d report(s)", len(reports))

    save_reports = settings["report"]["save_reports"]
    report_format = settings["report"]["format"]

    if not text_output and save_reports and report_format == "text":
        text_output = choose_default_export_path("scan", "txt")

    if not json_output and save_reports and report_format == "json":
        json_output = choose_default_export_path("scan", "json")

    if json_output == "STDOUT":
        payload = {
            "path": path,
            "report_count": len(reports),
            "reports": [asdict(report) for report in reports],
        }
        print(json.dumps(payload, indent=2))
    else:
        for index, report in enumerate(reports, start=1):
            print(f"\n{'=' * 20} Scan Report {index} {'=' * 20}")
            print(format_report(report))

    if text_output and json_output != "STDOUT":
        export_reports_text(reports, text_output)
        logger.info("Text scan report exported to: %s", text_output)
        print(f"\nText report exported to: {text_output}")

    if json_output and json_output != "STDOUT":
        export_reports_json(reports, json_output)
        logger.info("JSON scan report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    return EXIT_ANALYSIS_FOUND if reports else EXIT_SUCCESS


def run_trace(logger, path, text_output=None, json_output=None, settings=None, config_path="explainable.toml"):
    logger.info("Running trace preview on: %s", path)

    reports = scan_runtime(path, config_path=config_path)
    logger.info("Trace preview completed with %d report(s)", len(reports))

    save_reports = settings["report"]["save_reports"]
    report_format = settings["report"]["format"]

    if not text_output and save_reports and report_format == "text":
        text_output = choose_default_export_path("trace", "txt")

    if not json_output and save_reports and report_format == "json":
        json_output = choose_default_export_path("trace", "json")

    if json_output == "STDOUT":
        payload = {
            "path": path,
            "report_count": len(reports),
            "reports": [asdict(report) for report in reports],
        }
        print(json.dumps(payload, indent=2))
    else:
        print("\nRunning safe trace preview...\n")

        for index, report in enumerate(reports, start=1):
            print(f"\n{'=' * 20} Trace Report {index} {'=' * 20}")
            print(format_report(report))

        print("\nSafe trace preview complete.\n")

    if text_output and json_output != "STDOUT":
        export_reports_text(reports, text_output)
        logger.info("Text trace report exported to: %s", text_output)
        print(f"\nText report exported to: {text_output}")

    if json_output and json_output != "STDOUT":
        export_reports_json(reports, json_output)
        logger.info("JSON trace report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    return EXIT_ANALYSIS_FOUND if reports else EXIT_SUCCESS


def run_analyze_file(logger, file_path, function_name, text_output=None, json_output=None, settings=None):
    logger.info("Analyzing file: %s | function: %s", file_path, function_name)

    try:
        module = load_module_from_file(file_path)
        func = get_function_from_module(module, function_name)
    except (FileNotFoundError, ValueError, AttributeError, TypeError, ImportError) as exc:
        logger.warning("Analyze-file input error: %s: %s", type(exc).__name__, exc)

        if json_output == "STDOUT":
            print(json.dumps({
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            }, indent=2))
        else:
            print(f"Error: {type(exc).__name__}: {exc}")

        return EXIT_INPUT_ERROR

    save_reports = settings["report"]["save_reports"] if settings else False
    report_format = settings["report"]["format"] if settings else "text"

    if not text_output and save_reports and report_format == "text":
        text_output = choose_default_export_path("analyze", "txt")

    if not json_output and save_reports and report_format == "json":
        json_output = choose_default_export_path("analyze", "json")

    export_json_path = None if json_output == "STDOUT" else json_output

    report = analyze_function(
        func=func,
        variable_details={},
        related_functions=[],
        export_text_path=text_output,
        export_json_path=export_json_path,
        print_report=(json_output != "STDOUT"),
    )

    if report is None:
        logger.info("Function completed without runtime failure: %s", function_name)

        if json_output == "STDOUT":
            print(json.dumps({
                "file": file_path,
                "function": function_name,
                "status": "no_runtime_error",
                "report": None,
            }, indent=2))
        else:
            print(
                "The function completed without raising an exception. "
                "No runtime error report was generated."
            )

        return EXIT_SUCCESS

    logger.info("Runtime analysis found an issue in function: %s", function_name)

    if json_output == "STDOUT":
        print(json.dumps({
            "file": file_path,
            "function": function_name,
            "status": "runtime_issue_found",
            "report": asdict(report),
        }, indent=2))

    if text_output and json_output != "STDOUT":
        logger.info("Text analysis report exported to: %s", text_output)

    if export_json_path:
        logger.info("JSON analysis report exported to: %s", export_json_path)

    return EXIT_ANALYSIS_FOUND


def run_list_functions(logger, file_path, json_mode=False):
    logger.info("Listing zero-argument functions in file: %s", file_path)

    try:
        module = load_module_from_file(file_path)
        functions = get_zero_arg_functions(module)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        logger.warning("List-functions input error: %s: %s", type(exc).__name__, exc)
        print(f"Error: {type(exc).__name__}: {exc}")
        return EXIT_INPUT_ERROR

    names = sorted(functions.keys())

    if json_mode:
        print(json.dumps({"file": file_path, "functions": names}, indent=2))
        return EXIT_SUCCESS

    if not functions:
        logger.info("No zero-argument functions found in file: %s", file_path)
        print("\nNo zero-argument functions found.\n")
        return EXIT_SUCCESS

    print("\nZero-argument functions:\n")
    for name in names:
        print(f"- {name}")
    print("")

    logger.info("Found %d zero-argument function(s) in file: %s", len(functions), file_path)
    return EXIT_SUCCESS


def run_call_graph(logger, file_path, json_mode=False):
    logger.info("Building call graph for file: %s", file_path)

    graph = build_call_graph(file_path)

    if json_mode:
        serializable_graph = {
            func: sorted(list(calls))
            for func, calls in sorted(graph.items())
        }
        print(json.dumps({"file": file_path, "call_graph": serializable_graph}, indent=2))
        return EXIT_SUCCESS

    if not graph:
        print("No call graph could be generated.")
        return EXIT_SUCCESS

    print("\nCall Graph:\n")

    for func, calls in sorted(graph.items()):
        if not calls:
            print(f"{func} -> (no calls)")
        else:
            for called in sorted(calls):
                print(f"{func} -> {called}")

    print("")
    return EXIT_SUCCESS


def run_bug_chain(logger, file_path, function_name, json_mode=False):
    logger.info("Tracing bug chain for file: %s | target function: %s", file_path, function_name)

    chains = find_bug_chains(file_path, function_name)

    if json_mode:
        print(json.dumps({
            "file": file_path,
            "target_function": function_name,
            "chains": chains,
        }, indent=2))
        return EXIT_SUCCESS

    if not chains:
        print(f"\nNo bug chain found for target function: {function_name}\n")
        return EXIT_SUCCESS

    print(f"\nBug Chain(s) leading to `{function_name}`:\n")

    for index, chain in enumerate(chains, start=1):
        print(f"Chain {index}: " + " -> ".join(chain))

    print("")
    return EXIT_SUCCESS


def run_perf(logger, file_path, json_mode=False, fail_on=None, fail_count=None):
    logger.info("Running performance heuristic analysis on file: %s", file_path)

    report = scan_python_file(file_path)
    qualifying_count = count_findings_at_or_above_threshold(
        report.performance_scored_findings,
        fail_on,
    )
    triggered = threshold_triggered_from_findings(
        report.performance_scored_findings,
        fail_on,
        fail_count,
    )

    if json_mode:
        print(json.dumps({
            "file": file_path,
            "fail_on": fail_on,
            "fail_count": fail_count,
            "qualifying_finding_count": qualifying_count,
            "threshold_triggered": triggered,
            "report": asdict(report),
        }, indent=2))
        return EXIT_ANALYSIS_FOUND if triggered else EXIT_SUCCESS

    print("\nPerformance Heuristic Report:\n")
    print(format_report(report))
    if fail_on:
        print(f"\nFail threshold: {fail_on}")
    if fail_count is not None:
        print(f"Fail count: {fail_count}")
    print(f"Qualifying finding count: {qualifying_count}")
    print(f"Threshold triggered: {triggered}")
    print("")

    return EXIT_ANALYSIS_FOUND if triggered else EXIT_SUCCESS


def run_perf_summary(logger, path, json_mode=False, config_path="explainable.toml", fail_on=None, fail_count=None, top=10, sort_by="severity"):
    logger.info("Running performance summary for project: %s", path)

    payload = build_perf_summary_payload(
        path=path,
        config_path=config_path,
        fail_on=fail_on,
        fail_count=fail_count,
        top=top,
        sort_by=sort_by,
    )

    if json_mode:
        print(json.dumps(payload, indent=2))
        return EXIT_ANALYSIS_FOUND if payload["threshold_triggered"] else EXIT_SUCCESS

    print("\nPerformance Summary:\n")
    print(f"Path: {path}")
    print(f"Total files scanned: {payload['total_files_scanned']}")
    print(f"Files with findings: {payload['files_with_findings']}")
    print(f"Highest severity found: {payload['highest_severity_found'] or 'none'}")
    totals = payload["total_severity_summary"]
    print(
        "Total severity summary: "
        f"high={totals['high']}, medium={totals['medium']}, low={totals['low']}"
    )

    if fail_on:
        print(f"Fail threshold: {fail_on}")
    if fail_count is not None:
        print(f"Fail count: {fail_count}")
    print(f"Qualifying finding count: {payload['qualifying_finding_count']}")
    print(f"Threshold triggered: {payload['threshold_triggered']}")
    print(f"Sort by: {sort_by}")
    print(f"Top limit: {top}")

    print("\nTop files by severity:\n")
    top_files = payload["top_files"]
    if not top_files:
        print("(no files with findings)")
    else:
        for item in top_files:
            print(
                f"- {item['file_name']} | "
                f"severity={item['overall_severity']} | "
                f"findings={item['finding_count']} | "
                f"high={item['severity_summary'].get('high', 0)}, "
                f"medium={item['severity_summary'].get('medium', 0)}, "
                f"low={item['severity_summary'].get('low', 0)}"
            )

    print("")
    return EXIT_ANALYSIS_FOUND if payload["threshold_triggered"] else EXIT_SUCCESS


def run_perf_compare(logger, path, baseline_path, text_output=None, json_output=None, config_path="explainable.toml", top=10, sort_by="severity"):
    logger.info("Running performance comparison for project: %s", path)
    logger.info("Using baseline file: %s", baseline_path)

    try:
        baseline = load_json_file(baseline_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        if json_output == "STDOUT":
            print(json.dumps({
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            }, indent=2))
        else:
            print(f"Error: {type(exc).__name__}: {exc}")
        return EXIT_INPUT_ERROR

    current = build_perf_summary_payload(
        path=path,
        config_path=config_path,
        fail_on=None,
        fail_count=None,
        top=top,
        sort_by=sort_by,
    )

    comparison = compare_perf_summaries(current, baseline)
    text_report = render_perf_compare_text(comparison)

    if json_output == "STDOUT":
        print(json.dumps(comparison, indent=2))
    else:
        print("")
        print(text_report)
        print("")

    if text_output and json_output != "STDOUT":
        write_text_file(text_output, text_report)
        logger.info("Text comparison report exported to: %s", text_output)
        print(f"Text report exported to: {text_output}")

    if json_output and json_output != "STDOUT":
        write_json_file(json_output, comparison)
        logger.info("JSON comparison report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    return EXIT_ANALYSIS_FOUND if comparison["regression_detected"] else EXIT_SUCCESS