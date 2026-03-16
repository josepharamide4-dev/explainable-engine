import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path
from fnmatch import fnmatch

from config.settings import load_settings
from core.baseline import (
    approve_current_findings,
    build_baseline_payload,
    build_regression_payload,
    load_baseline,
    prune_baseline_payload,
    refresh_baseline_payload,
    render_regression_text,
    save_baseline,
)
from core.bug_chain import find_bug_chains
from core.call_graph import build_call_graph
from core.context_enrichment import (
    enrich_perf_payload,
    enrich_report_context,
    render_team_context_text,
)
from core.file_loader import (
    get_function_from_module,
    get_zero_arg_functions,
    load_module_from_file,
)
from core.incremental import (
    build_scan_state,
    incremental_scan,
    render_incremental,
    save_state,
)
from core.logger import setup_logger
from core.runner import analyze_function
from core.runtime_scanner import scan_runtime
from core.scanner import scan_project, scan_python_file
from core.trends import (
    append_history_snapshot,
    build_trend_report,
    load_history,
    render_trend_report_text,
    save_history,
)
from core.triage import (
    build_triage_items,
    create_triage_tasks,
    render_triage_report_text,
    sync_triage_tasks,
)
from core.work_cli import (
    run_member_add,
    run_note_add,
    run_note_show,
    run_work_add,
    run_work_assign,
    run_work_board,
    run_work_handover,
    run_work_update,
)
from reporting.exporter import export_reports_json, export_reports_text
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
    scan_parser.add_argument("--viewer", dest="viewer", default="")

    incremental_state_init_parser = subparsers.add_parser(
        "incremental-state-init",
        help="Create or refresh the incremental scan state file",
    )
    incremental_state_init_parser.add_argument("path")
    incremental_state_init_parser.add_argument("--state", required=True, dest="state_path")
    incremental_state_init_parser.add_argument("--json", action="store_true", dest="json_mode")

    incremental_scan_parser = subparsers.add_parser(
        "incremental-scan",
        help="Scan only changed Python files using a saved scan state file",
    )
    incremental_scan_parser.add_argument("path")
    incremental_scan_parser.add_argument("--state", required=True, dest="state_path")
    incremental_scan_parser.add_argument("--json", action="store_true", dest="json_mode")

    trace_parser = subparsers.add_parser(
        "trace",
        help="Safely preview functions across a project without executing them",
    )
    trace_parser.add_argument("path")
    trace_parser.add_argument("--text", dest="text_output")
    trace_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")

    analyze_file_parser = subparsers.add_parser(
        "analyze-file",
        help="Analyze a real function from a real Python file",
    )
    analyze_file_parser.add_argument("file_path")
    analyze_file_parser.add_argument("--function", required=True, dest="function_name")
    analyze_file_parser.add_argument("--text", dest="text_output")
    analyze_file_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")

    list_functions_parser = subparsers.add_parser(
        "list-functions",
        help="List zero-argument functions in a Python file",
    )
    list_functions_parser.add_argument("file_path")
    list_functions_parser.add_argument("--json", action="store_true", dest="json_mode")

    call_graph_parser = subparsers.add_parser(
        "call-graph",
        help="Build a function call graph for a Python file",
    )
    call_graph_parser.add_argument("file_path")
    call_graph_parser.add_argument("--json", action="store_true", dest="json_mode")

    bug_chain_parser = subparsers.add_parser(
        "bug-chain",
        help="Trace likely caller chains leading to a target function",
    )
    bug_chain_parser.add_argument("file_path")
    bug_chain_parser.add_argument("--function", required=True, dest="function_name")
    bug_chain_parser.add_argument("--json", action="store_true", dest="json_mode")

    perf_parser = subparsers.add_parser(
        "perf",
        help="Analyze a Python file for performance-related heuristics",
    )
    perf_parser.add_argument("file_path")
    perf_parser.add_argument("--json", action="store_true", dest="json_mode")
    perf_parser.add_argument("--viewer", dest="viewer", default="")
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
        help="Aggregate performance findings across a whole project",
    )
    perf_summary_parser.add_argument("path")
    perf_summary_parser.add_argument("--json", action="store_true", dest="json_mode")
    perf_summary_parser.add_argument("--viewer", dest="viewer", default="")
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
        dest="top",
        help="Maximum number of files to show in the summary",
    )
    perf_summary_parser.add_argument(
        "--sort-by",
        choices=["severity", "findings", "file"],
        dest="sort_by",
        help="How to sort files in the summary",
    )
    perf_summary_parser.add_argument("--ignore-file", dest="ignore_file")
    perf_summary_parser.add_argument("--include-file", dest="include_file")

    perf_baseline_parser = subparsers.add_parser(
        "perf-baseline",
        help="Create and save a performance baseline snapshot",
    )
    perf_baseline_parser.add_argument("path")
    perf_baseline_parser.add_argument("--text", dest="text_output")
    perf_baseline_parser.add_argument("--json", dest="json_output")
    perf_baseline_parser.add_argument(
        "--top",
        type=int,
        dest="top",
        help="Maximum number of files to include in the baseline summary",
    )
    perf_baseline_parser.add_argument(
        "--sort-by",
        choices=["severity", "findings", "file"],
        dest="sort_by",
        help="How to sort files in the baseline summary",
    )
    perf_baseline_parser.add_argument("--ignore-file", dest="ignore_file")
    perf_baseline_parser.add_argument("--include-file", dest="include_file")

    perf_compare_parser = subparsers.add_parser(
        "perf-compare",
        help="Compare current performance summary against a saved JSON baseline",
    )
    perf_compare_parser.add_argument("path")
    perf_compare_parser.add_argument("--baseline", required=True, dest="baseline_path")
    perf_compare_parser.add_argument("--text", dest="text_output")
    perf_compare_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")
    perf_compare_parser.add_argument(
        "--top",
        type=int,
        dest="top",
        help="Maximum number of files to include in the generated summary before comparison",
    )
    perf_compare_parser.add_argument(
        "--sort-by",
        choices=["severity", "findings", "file"],
        dest="sort_by",
        help="How to sort files in the generated summary before comparison",
    )
    perf_compare_parser.add_argument("--ignore-file", dest="ignore_file")
    perf_compare_parser.add_argument("--include-file", dest="include_file")

    baseline_create_parser = subparsers.add_parser(
        "baseline-create",
        help="Create a finding baseline for the current project scan",
    )
    baseline_create_parser.add_argument("path")
    baseline_create_parser.add_argument("--output", required=True)
    baseline_create_parser.add_argument("--json", action="store_true", dest="json_mode")

    baseline_compare_parser = subparsers.add_parser(
        "baseline-compare",
        help="Compare current findings against a saved baseline",
    )
    baseline_compare_parser.add_argument("path")
    baseline_compare_parser.add_argument("--baseline", required=True, dest="baseline_path")
    baseline_compare_parser.add_argument("--viewer", dest="viewer", default="")
    baseline_compare_parser.add_argument("--json", action="store_true", dest="json_mode")

    baseline_approve_parser = subparsers.add_parser(
        "baseline-approve",
        help="Approve current findings into an existing baseline file",
    )
    baseline_approve_parser.add_argument("path")
    baseline_approve_parser.add_argument("--baseline", required=True, dest="baseline_path")
    baseline_approve_parser.add_argument("--json", action="store_true", dest="json_mode")

    baseline_refresh_parser = subparsers.add_parser(
        "baseline-refresh",
        help="Refresh an existing baseline file from the current project state",
    )
    baseline_refresh_parser.add_argument("path")
    baseline_refresh_parser.add_argument("--baseline", required=True, dest="baseline_path")
    baseline_refresh_parser.add_argument("--json", action="store_true", dest="json_mode")

    baseline_prune_parser = subparsers.add_parser(
        "baseline-prune",
        help="Remove resolved findings from an existing baseline without accepting new ones",
    )
    baseline_prune_parser.add_argument("path")
    baseline_prune_parser.add_argument("--baseline", required=True, dest="baseline_path")
    baseline_prune_parser.add_argument("--json", action="store_true", dest="json_mode")

    triage_report_parser = subparsers.add_parser(
        "triage-report",
        help="Show triage information for new regressions",
    )
    triage_report_parser.add_argument("path")
    triage_report_parser.add_argument("--baseline", required=True, dest="baseline_path")
    triage_report_parser.add_argument("--viewer", dest="viewer", default="")
    triage_report_parser.add_argument("--json", action="store_true", dest="json_mode")

    triage_create_parser = subparsers.add_parser(
        "triage-create",
        help="Create work items for new regressions that are not yet tracked",
    )
    triage_create_parser.add_argument("path")
    triage_create_parser.add_argument("--baseline", required=True, dest="baseline_path")
    triage_create_parser.add_argument("--viewer", dest="viewer", default="")
    triage_create_parser.add_argument("--json", action="store_true", dest="json_mode")

    triage_sync_parser = subparsers.add_parser(
        "triage-sync",
        help="Sync regression tasks against current regression state",
    )
    triage_sync_parser.add_argument("path")
    triage_sync_parser.add_argument("--baseline", required=True, dest="baseline_path")
    triage_sync_parser.add_argument("--viewer", dest="viewer", default="")
    triage_sync_parser.add_argument("--json", action="store_true", dest="json_mode")

    history_snapshot_parser = subparsers.add_parser(
        "history-snapshot",
        help="Append a regression snapshot to a history file",
    )
    history_snapshot_parser.add_argument("path")
    history_snapshot_parser.add_argument("--baseline", required=True, dest="baseline_path")
    history_snapshot_parser.add_argument("--history", required=True, dest="history_path")
    history_snapshot_parser.add_argument("--viewer", dest="viewer", default="")
    history_snapshot_parser.add_argument("--json", action="store_true", dest="json_mode")

    trend_report_parser = subparsers.add_parser(
        "trend-report",
        help="Build a trend report from a history file",
    )
    trend_report_parser.add_argument("--history", required=True, dest="history_path")
    trend_report_parser.add_argument("--json", action="store_true", dest="json_mode")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check whether the Explainable setup is healthy",
    )
    doctor_parser.add_argument("--text", dest="text_output")
    doctor_parser.add_argument("--json", nargs="?", const="STDOUT", dest="json_output")
    doctor_parser.add_argument("--json-stdout", action="store_true", dest="json_stdout")
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        dest="strict_mode",
        help="Treat warnings as CI failures and mark the report as strict",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Run full project analysis (doctor + scan + perf-summary + regression)",
    )
    check_parser.add_argument("path")
    check_parser.add_argument("--json", action="store_true", dest="json_mode")
    check_parser.add_argument("--viewer", dest="viewer", default="")
    check_parser.add_argument("--baseline", dest="baseline_path")

    member_add_parser = subparsers.add_parser(
        "member-add",
        help="Add or update a project member in the shared worklog",
    )
    member_add_parser.add_argument("--name", required=True)
    member_add_parser.add_argument("--role")
    member_add_parser.add_argument("--inactive", action="store_true")
    member_add_parser.add_argument("--influence-files", dest="influence_files")
    member_add_parser.add_argument("--influence-findings", dest="influence_findings")
    member_add_parser.add_argument("--notes")
    member_add_parser.add_argument("--json", action="store_true", dest="json_mode")

    work_add_parser = subparsers.add_parser(
        "work-add",
        help="Create a work item in the shared worklog",
    )
    work_add_parser.add_argument("--id", required=True)
    work_add_parser.add_argument("--title", required=True)
    work_add_parser.add_argument("--owner")
    work_add_parser.add_argument("--assignees")
    work_add_parser.add_argument("--files")
    work_add_parser.add_argument("--finding-ids", dest="finding_ids")
    work_add_parser.add_argument("--notes")
    work_add_parser.add_argument("--blockers")
    work_add_parser.add_argument("--collaborators")
    work_add_parser.add_argument("--watchers")
    work_add_parser.add_argument("--json", action="store_true", dest="json_mode")

    work_update_parser = subparsers.add_parser(
        "work-update",
        help="Update an existing work item",
    )
    work_update_parser.add_argument("--id", required=True)
    work_update_parser.add_argument("--title")
    work_update_parser.add_argument(
        "--status",
        choices=["todo", "in_progress", "blocked", "review", "done"],
    )
    work_update_parser.add_argument("--files")
    work_update_parser.add_argument("--finding-ids", dest="finding_ids")
    work_update_parser.add_argument("--notes")
    work_update_parser.add_argument("--blockers")
    work_update_parser.add_argument("--collaborators")
    work_update_parser.add_argument("--watchers")
    work_update_parser.add_argument("--json", action="store_true", dest="json_mode")

    work_assign_parser = subparsers.add_parser(
        "work-assign",
        help="Assign people to an existing work item",
    )
    work_assign_parser.add_argument("--id", required=True)
    work_assign_parser.add_argument("--people", required=True)
    work_assign_parser.add_argument("--primary-owner", dest="primary_owner")
    work_assign_parser.add_argument("--reason")
    work_assign_parser.add_argument("--json", action="store_true", dest="json_mode")

    work_handover_parser = subparsers.add_parser(
        "work-handover",
        help="Hand over a work item from one person to another",
    )
    work_handover_parser.add_argument("--id", required=True)
    work_handover_parser.add_argument("--from-person", required=True, dest="from_person")
    work_handover_parser.add_argument("--to-person", required=True, dest="to_person")
    work_handover_parser.add_argument("--reason")
    work_handover_parser.add_argument("--json", action="store_true", dest="json_mode")

    work_board_parser = subparsers.add_parser(
        "work-board",
        help="Show the current shared work board",
    )
    work_board_parser.add_argument("--json", action="store_true", dest="json_mode")

    note_add_parser = subparsers.add_parser(
        "note-add",
        help="Create a code-linked team note",
    )
    note_add_parser.add_argument("--id", required=True)
    note_add_parser.add_argument("--author", required=True)
    note_add_parser.add_argument("--body", required=True)
    note_add_parser.add_argument(
        "--visibility",
        choices=["project", "restricted"],
        default="project",
    )
    note_add_parser.add_argument("--files")
    note_add_parser.add_argument("--lines")
    note_add_parser.add_argument("--finding-ids", dest="finding_ids")
    note_add_parser.add_argument("--task-ids", dest="task_ids")
    note_add_parser.add_argument("--shared-with", dest="shared_with")
    note_add_parser.add_argument("--tags")
    note_add_parser.add_argument("--handover", action="store_true")
    note_add_parser.add_argument("--json", action="store_true", dest="json_mode")

    note_show_parser = subparsers.add_parser(
        "note-show",
        help="Show notes relevant to a file, line, or finding",
    )
    note_show_parser.add_argument("--file")
    note_show_parser.add_argument("--line", type=int)
    note_show_parser.add_argument("--finding-id", dest="finding_id")
    note_show_parser.add_argument("--viewer")
    note_show_parser.add_argument("--json", action="store_true", dest="json_mode")

    args = parser.parse_args()

    if args.quiet and args.verbose:
        print("Error: --quiet and --verbose cannot be used together.")
        return EXIT_INPUT_ERROR

    if hasattr(args, "fail_count") and args.fail_count is not None and args.fail_count < 1:
        print("Error: --fail-count must be at least 1.")
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
            return run_scan(
                logger,
                args.path,
                args.text_output,
                args.json_output,
                settings,
                args.config,
                args.viewer,
            )

        if args.command == "incremental-state-init":
            return run_incremental_state_init(
                logger,
                args.path,
                args.state_path,
                args.json_mode,
            )

        if args.command == "incremental-scan":
            return run_incremental_scan(
                logger,
                args.path,
                args.state_path,
                args.json_mode,
            )

        if args.command == "trace":
            return run_trace(
                logger,
                args.path,
                args.text_output,
                args.json_output,
                settings,
                args.config,
            )

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
            return run_perf(
                logger,
                args.file_path,
                args.json_mode,
                args.fail_on,
                args.fail_count,
                args.viewer,
            )

        if args.command == "perf-summary":
            resolved_top, resolved_sort_by, resolved_ignore_file, resolved_include_file = resolve_perf_options(
                settings=settings,
                top=args.top,
                sort_by=args.sort_by,
                ignore_file=args.ignore_file,
                include_file=args.include_file,
            )
            return run_perf_summary(
                logger,
                args.path,
                args.json_mode,
                args.config,
                args.fail_on,
                args.fail_count,
                resolved_top,
                resolved_sort_by,
                resolved_ignore_file,
                resolved_include_file,
                args.viewer,
            )

        if args.command == "perf-baseline":
            resolved_top, resolved_sort_by, resolved_ignore_file, resolved_include_file = resolve_perf_options(
                settings=settings,
                top=args.top,
                sort_by=args.sort_by,
                ignore_file=args.ignore_file,
                include_file=args.include_file,
            )
            return run_perf_baseline(
                logger,
                args.path,
                args.text_output,
                args.json_output,
                args.config,
                resolved_top,
                resolved_sort_by,
                resolved_ignore_file,
                resolved_include_file,
            )

        if args.command == "perf-compare":
            resolved_top, resolved_sort_by, resolved_ignore_file, resolved_include_file = resolve_perf_options(
                settings=settings,
                top=args.top,
                sort_by=args.sort_by,
                ignore_file=args.ignore_file,
                include_file=args.include_file,
            )
            return run_perf_compare(
                logger,
                args.path,
                args.baseline_path,
                args.text_output,
                args.json_output,
                args.config,
                resolved_top,
                resolved_sort_by,
                resolved_ignore_file,
                resolved_include_file,
            )

        if args.command == "baseline-create":
            return run_baseline_create(logger, args.path, args.output, args.json_mode, args.config)

        if args.command == "baseline-compare":
            return run_baseline_compare(
                logger,
                args.path,
                args.baseline_path,
                args.viewer,
                args.json_mode,
                args.config,
            )

        if args.command == "baseline-approve":
            return run_baseline_approve(logger, args.path, args.baseline_path, args.json_mode, args.config)

        if args.command == "baseline-refresh":
            return run_baseline_refresh(logger, args.path, args.baseline_path, args.json_mode, args.config)

        if args.command == "baseline-prune":
            return run_baseline_prune(logger, args.path, args.baseline_path, args.json_mode, args.config)

        if args.command == "triage-report":
            return run_triage_report(
                logger,
                args.path,
                args.baseline_path,
                args.viewer,
                args.json_mode,
                args.config,
            )

        if args.command == "triage-create":
            return run_triage_create(
                logger,
                args.path,
                args.baseline_path,
                args.viewer,
                args.json_mode,
                args.config,
            )

        if args.command == "triage-sync":
            return run_triage_sync(
                logger,
                args.path,
                args.baseline_path,
                args.viewer,
                args.json_mode,
                args.config,
            )

        if args.command == "history-snapshot":
            return run_history_snapshot(
                logger,
                args.path,
                args.baseline_path,
                args.history_path,
                args.viewer,
                args.json_mode,
                args.config,
            )

        if args.command == "trend-report":
            return run_trend_report(logger, args.history_path, args.json_mode)

        if args.command == "doctor":
            return run_doctor(
                logger=logger,
                config_path=args.config,
                settings=settings,
                text_output=args.text_output,
                json_output=args.json_output,
                json_stdout=args.json_stdout,
                strict_mode=args.strict_mode,
            )

        if args.command == "check":
            return run_check(
                logger=logger,
                path=args.path,
                json_mode=args.json_mode,
                config_path=args.config,
                settings=settings,
                viewer=args.viewer,
                baseline_path=args.baseline_path,
            )

        if args.command == "member-add":
            return run_member_add(args)

        if args.command == "work-add":
            return run_work_add(args)

        if args.command == "work-update":
            return run_work_update(args)

        if args.command == "work-assign":
            return run_work_assign(args)

        if args.command == "work-handover":
            return run_work_handover(args)

        if args.command == "work-board":
            return run_work_board(args)

        if args.command == "note-add":
            return run_note_add(args)

        if args.command == "note-show":
            return run_note_show(args)

        parser.print_help()
        return EXIT_INPUT_ERROR

    except Exception as exc:
        logger.exception("Internal CLI failure")
        print(f"Internal error: {type(exc).__name__}: {exc}")
        return EXIT_INTERNAL_ERROR


def resolve_perf_options(settings, top=None, sort_by=None, ignore_file=None, include_file=None):
    perf_settings = settings.get("perf", {}) if settings else {}

    resolved_top = top if top is not None else perf_settings.get("top", 10)
    resolved_sort_by = sort_by if sort_by is not None else perf_settings.get("sort_by", "severity")
    resolved_ignore_file = ignore_file if ignore_file is not None else perf_settings.get("ignore_file", "")
    resolved_include_file = include_file if include_file is not None else perf_settings.get("include_file", "")

    if resolved_top < 1:
        raise ValueError("Resolved perf top must be at least 1.")

    if resolved_sort_by not in {"severity", "findings", "file"}:
        raise ValueError("Resolved perf sort_by must be one of: severity, findings, file.")

    return resolved_top, resolved_sort_by, resolved_ignore_file, resolved_include_file


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


def load_pattern_file(pattern_file: str | None, label: str) -> list[str]:
    if not pattern_file:
        return []

    path = Path(pattern_file)
    if not path.exists():
        raise FileNotFoundError(f"{label} file not found: {pattern_file}")

    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)

    return patterns


def matches_path_pattern(relative_path: str, pattern: str) -> bool:
    normalized_path = relative_path.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")

    if normalized_pattern.endswith("/"):
        prefix = normalized_pattern.rstrip("/") + "/"
        return normalized_path.startswith(prefix)

    return fnmatch(normalized_path, normalized_pattern) or normalized_path == normalized_pattern


def filter_reports_by_path_rules(reports, base_path: str, include_patterns: list[str], ignore_patterns: list[str]):
    base = Path(base_path).resolve()
    filtered = []

    for report in reports:
        report_path = Path(report.file_name).resolve()
        try:
            relative_path = report_path.relative_to(base).as_posix()
        except ValueError:
            relative_path = report_path.name

        if include_patterns:
            included = any(matches_path_pattern(relative_path, pattern) for pattern in include_patterns)
            if not included:
                continue

        ignored = any(matches_path_pattern(relative_path, pattern) for pattern in ignore_patterns)
        if ignored:
            continue

        filtered.append(report)

    return filtered


def build_perf_summary_payload(
    path,
    config_path="explainable.toml",
    fail_on=None,
    fail_count=None,
    top=10,
    sort_by="severity",
    ignore_file=None,
    include_file=None,
):
    reports = scan_project(path, config_path=config_path)
    ignore_patterns = load_pattern_file(ignore_file, "Ignore")
    include_patterns = load_pattern_file(include_file, "Include")
    reports = filter_reports_by_path_rules(
        reports=reports,
        base_path=path,
        include_patterns=include_patterns,
        ignore_patterns=ignore_patterns,
    )

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
        "ignore_file": ignore_file,
        "ignore_patterns": ignore_patterns,
        "include_file": include_file,
        "include_patterns": include_patterns,
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


def render_perf_summary_text(payload: dict) -> str:
    lines = [
        "Performance Summary:",
        "",
        f"Path: {payload['path']}",
        f"Total files scanned: {payload['total_files_scanned']}",
        f"Files with findings: {payload['files_with_findings']}",
        f"Highest severity found: {payload['highest_severity_found'] or 'none'}",
    ]

    totals = payload["total_severity_summary"]
    lines.append(
        "Total severity summary: "
        f"high={totals['high']}, medium={totals['medium']}, low={totals['low']}"
    )

    if payload.get("include_file"):
        lines.append(f"Include file: {payload['include_file']}")
    if payload.get("ignore_file"):
        lines.append(f"Ignore file: {payload['ignore_file']}")

    if payload.get("fail_on"):
        lines.append(f"Fail threshold: {payload['fail_on']}")
    if payload.get("fail_count") is not None:
        lines.append(f"Fail count: {payload['fail_count']}")

    lines.extend(
        [
            f"Qualifying finding count: {payload['qualifying_finding_count']}",
            f"Threshold triggered: {payload['threshold_triggered']}",
            f"Sort by: {payload['sort_by']}",
            f"Top limit: {payload['top']}",
            "",
            "Top files by severity:",
            "",
        ]
    )

    top_files = payload["top_files"]
    if not top_files:
        lines.append("(no files with findings)")
    else:
        for item in top_files:
            lines.append(
                f"- {item['file_name']} | "
                f"severity={item['overall_severity']} | "
                f"findings={item['finding_count']} | "
                f"high={item['severity_summary'].get('high', 0)}, "
                f"medium={item['severity_summary'].get('medium', 0)}, "
                f"low={item['severity_summary'].get('low', 0)}"
            )

            team_text = render_team_context_text(item.get("team_context", {}))
            if team_text:
                for line in team_text.splitlines():
                    lines.append(f"  {line}")

    return "\n".join(lines)


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


def build_doctor_payload(config_path: str, settings: dict, strict_mode: bool = False) -> dict:
    checks = []

    def add_check(name: str, status: str, message: str, fix_hint: str = ""):
        checks.append(
            {
                "name": name,
                "status": status,
                "message": message,
                "fix_hint": fix_hint,
            }
        )

    config_file = Path(config_path)
    if config_file.exists():
        add_check(
            "config_file",
            "pass",
            f"Config file found: {config_path}",
            "",
        )
    else:
        add_check(
            "config_file",
            "pass",
            f"Config file not found, using defaults: {config_path}",
            "Create explainable.toml in the project root if you want custom defaults.",
        )

    try:
        perf_settings = settings.get("perf", {})
        top = perf_settings.get("top", 10)
        sort_by = perf_settings.get("sort_by", "severity")

        if isinstance(top, int) and top >= 1:
            add_check("perf_top", "pass", f"Perf top is valid: {top}")
        else:
            add_check(
                "perf_top",
                "fail",
                f"Perf top must be an integer >= 1, got: {top!r}",
                'Set [perf].top to 1 or higher in explainable.toml, for example: top = 5',
            )

        if sort_by in {"severity", "findings", "file"}:
            add_check("perf_sort_by", "pass", f"Perf sort_by is valid: {sort_by}")
        else:
            add_check(
                "perf_sort_by",
                "fail",
                f"Perf sort_by is invalid: {sort_by!r}",
                'Set [perf].sort_by to one of: "severity", "findings", or "file".',
            )
    except Exception as exc:
        add_check(
            "perf_config",
            "fail",
            f"Perf config validation failed: {type(exc).__name__}: {exc}",
            "Open explainable.toml and fix the [perf] section values.",
        )

    ignore_file = settings.get("perf", {}).get("ignore_file", "")
    include_file = settings.get("perf", {}).get("include_file", "")

    if ignore_file:
        if Path(ignore_file).exists():
            add_check("ignore_file", "pass", f"Ignore file exists: {ignore_file}")
        else:
            add_check(
                "ignore_file",
                "warn",
                f"Ignore file does not exist: {ignore_file}",
                f'Create the file "{ignore_file}" or set [perf].ignore_file = "" in explainable.toml.',
            )
    else:
        add_check("ignore_file", "pass", "No default ignore file configured.")

    if include_file:
        if Path(include_file).exists():
            add_check("include_file", "pass", f"Include file exists: {include_file}")
        else:
            add_check(
                "include_file",
                "warn",
                f"Include file does not exist: {include_file}",
                f'Create the file "{include_file}" or set [perf].include_file = "" in explainable.toml.',
            )
    else:
        add_check("include_file", "pass", "No default include file configured.")

    logs_dir = Path("logs")
    try:
        logs_dir.mkdir(exist_ok=True)
        test_file = logs_dir / ".doctor_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        add_check("logs_directory", "pass", f"Logs directory is writable: {logs_dir}")
    except Exception as exc:
        add_check(
            "logs_directory",
            "fail",
            f"Logs directory is not writable: {type(exc).__name__}: {exc}",
            "Create a writable logs folder in the project root or fix folder permissions.",
        )

    for path_str in ["main.py", "core", "reporting", "config"]:
        path_obj = Path(path_str)
        if path_obj.exists():
            add_check("project_path", "pass", f"Found required path: {path_str}")
        else:
            add_check(
                "project_path",
                "fail",
                f"Missing required path: {path_str}",
                f'Create or restore "{path_str}" in the project root.',
            )

    status_rank = {"pass": 0, "warn": 1, "fail": 2}
    overall_status = "pass"
    for check in checks:
        if status_rank[check["status"]] > status_rank[overall_status]:
            overall_status = check["status"]

    return {
        "config_path": config_path,
        "strict_mode": strict_mode,
        "overall_status": overall_status,
        "check_count": len(checks),
        "checks": checks,
    }


def render_doctor_text(payload: dict) -> str:
    lines = [
        "Explainable Doctor Report:",
        "",
        f"Config path: {payload['config_path']}",
        f"Strict mode: {payload['strict_mode']}",
        f"Overall status: {payload['overall_status']}",
        f"Checks run: {payload['check_count']}",
        "",
        "Checks:",
    ]

    for check in payload["checks"]:
        lines.append(f"- [{check['status'].upper()}] {check['name']}: {check['message']}")
        if check.get("fix_hint"):
            lines.append(f"  Fix: {check['fix_hint']}")

    return "\n".join(lines)


def render_check_text(payload: dict) -> str:
    lines = [
        "Explainable Check Report:",
        "",
        f"Path: {payload['path']}",
        f"Doctor status: {payload['doctor']['overall_status']}",
        f"Scan reports: {payload['scan']['report_count']}",
        f"Perf highest severity: {payload['perf_summary']['highest_severity_found'] or 'none'}",
        f"Perf files with findings: {payload['perf_summary']['files_with_findings']}",
        f"Perf threshold triggered: {payload['perf_summary']['threshold_triggered']}",
    ]

    if payload.get("regression"):
        regression = payload["regression"]
        lines.extend(
            [
                "",
                "Regression Summary:",
                f"New findings: {regression['new_finding_count']}",
                f"Resolved findings: {regression['resolved_finding_count']}",
                f"Existing findings: {regression['existing_finding_count']}",
                f"Regression detected: {regression['regression_detected']}",
            ]
        )

    lines.extend(["", "Perf Top Files With Team Context:"])

    for item in payload["perf_summary"]["top_files"]:
        lines.append(
            f"- {item['file_name']} | severity={item['overall_severity']} | findings={item['finding_count']}"
        )
        team_text = render_team_context_text(item.get("team_context", {}))
        if team_text:
            for line in team_text.splitlines():
                lines.append(f"  {line}")

    if payload.get("regression") and payload["regression"]["new_findings"]:
        lines.extend(["", "New regressions with team context:"])
        for item in payload["regression"]["new_findings"]:
            lines.append(
                f"- {item['file_name']} | line={item['line']} | severity={item['severity']} | id={item['id']}"
            )
            lines.append(f"  Message: {item['message']}")
            team_text = render_team_context_text(item.get("team_context", {}))
            if team_text:
                for line in team_text.splitlines():
                    lines.append(f"  {line}")

    return "\n".join(lines)


def run_scan(logger, path, text_output=None, json_output=None, settings=None, config_path="explainable.toml", viewer=""):
    logger.info("Scanning project: %s", path)

    reports = scan_project(path, config_path=config_path)
    logger.info("Scan completed with %d report(s)", len(reports))

    save_reports = settings["report"]["save_reports"]
    report_format = settings["report"]["format"]

    if not text_output and save_reports and report_format == "text":
        text_output = choose_default_export_path("scan", "txt")

    if not json_output and save_reports and report_format == "json":
        json_output = choose_default_export_path("scan", "json")

    enriched_reports = [enrich_report_context(report, viewer=viewer) for report in reports]

    if json_output == "STDOUT":
        payload = {
            "path": path,
            "report_count": len(enriched_reports),
            "reports": enriched_reports,
        }
        print(json.dumps(payload, indent=2))
    else:
        for index, report in enumerate(reports, start=1):
            print(f"\n{'=' * 20} Scan Report {index} {'=' * 20}")
            print(format_report(report))

            team_text = render_team_context_text(
                enrich_report_context(report, viewer=viewer).get("team_context", {})
            )
            if team_text:
                print("")
                print(team_text)

    if text_output and json_output != "STDOUT":
        export_reports_text(reports, text_output)
        logger.info("Text scan report exported to: %s", text_output)
        print(f"\nText report exported to: {text_output}")

    if json_output and json_output != "STDOUT":
        export_reports_json(reports, json_output)
        logger.info("JSON scan report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    return EXIT_ANALYSIS_FOUND if reports else EXIT_SUCCESS


def run_incremental_state_init(logger, path, state_path, json_mode):
    logger.info("Building incremental scan state for project: %s", path)

    payload = build_scan_state(path)
    save_state(payload, state_path)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Incremental state saved: {state_path}")
        print(f"Project path: {payload['project_path']}")
        print(f"Tracked files: {payload['file_count']}")
        print("")

    return EXIT_SUCCESS


def run_incremental_scan(logger, path, state_path, json_mode):
    logger.info("Running incremental scan for project: %s", path)

    payload = incremental_scan(
        project_path=path,
        state_path=state_path,
    )
    save_state(payload["new_state"], state_path)

    if json_mode:
        print(
            json.dumps(
                {
                    "changed_files": payload["changed_files"],
                    "removed_files": payload["removed_files"],
                    "reports": [asdict(report) for report in payload["reports"]],
                },
                indent=2,
            )
        )
    else:
        print("")
        print(render_incremental(payload))
        print("")

    return EXIT_ANALYSIS_FOUND if payload["reports"] else EXIT_SUCCESS


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

    lines = ["", "Call Graph:", ""]

    for func, calls in sorted(graph.items()):
        sorted_calls = sorted(calls)
        if not sorted_calls:
            lines.append(f"{func} -> (no calls)")
        else:
            lines.extend(f"{func} -> {called}" for called in sorted_calls)

    lines.append("")
    print("\n".join(lines))
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


def run_perf(logger, file_path, json_mode=False, fail_on=None, fail_count=None, viewer=""):
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

    enriched_report = enrich_report_context(report, viewer=viewer)

    if json_mode:
        print(json.dumps({
            "file": file_path,
            "fail_on": fail_on,
            "fail_count": fail_count,
            "qualifying_finding_count": qualifying_count,
            "threshold_triggered": triggered,
            "report": enriched_report,
        }, indent=2))
        return EXIT_ANALYSIS_FOUND if triggered else EXIT_SUCCESS

    print("\nPerformance Heuristic Report:\n")
    print(format_report(report))

    report_team_text = render_team_context_text(enriched_report.get("team_context", {}))
    if report_team_text:
        print("")
        print(report_team_text)

    if enriched_report.get("performance_scored_findings"):
        for finding in enriched_report["performance_scored_findings"]:
            finding_team_text = render_team_context_text(finding.get("team_context", {}))
            if finding_team_text:
                print("")
                print(f"Finding line {finding.get('line', 0)} context:")
                print(finding_team_text)

    if fail_on:
        print(f"\nFail threshold: {fail_on}")
    if fail_count is not None:
        print(f"Fail count: {fail_count}")
    print(f"Qualifying finding count: {qualifying_count}")
    print(f"Threshold triggered: {triggered}")
    print("")

    return EXIT_ANALYSIS_FOUND if triggered else EXIT_SUCCESS


def run_perf_summary(
    logger,
    path,
    json_mode=False,
    config_path="explainable.toml",
    fail_on=None,
    fail_count=None,
    top=10,
    sort_by="severity",
    ignore_file=None,
    include_file=None,
    viewer="",
):
    logger.info("Running performance summary for project: %s", path)

    try:
        payload = build_perf_summary_payload(
            path=path,
            config_path=config_path,
            fail_on=fail_on,
            fail_count=fail_count,
            top=top,
            sort_by=sort_by,
            ignore_file=ignore_file,
            include_file=include_file,
        )
    except FileNotFoundError as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        return EXIT_INPUT_ERROR

    enriched_payload = enrich_perf_payload(payload, viewer=viewer)

    if json_mode:
        print(json.dumps(enriched_payload, indent=2))
        return EXIT_ANALYSIS_FOUND if enriched_payload["threshold_triggered"] else EXIT_SUCCESS

    print("")
    print(render_perf_summary_text(enriched_payload))
    print("")
    return EXIT_ANALYSIS_FOUND if enriched_payload["threshold_triggered"] else EXIT_SUCCESS


def run_perf_baseline(
    logger,
    path,
    text_output=None,
    json_output=None,
    config_path="explainable.toml",
    top=10,
    sort_by="severity",
    ignore_file=None,
    include_file=None,
):
    logger.info("Creating performance baseline for project: %s", path)

    try:
        payload = build_perf_summary_payload(
            path=path,
            config_path=config_path,
            fail_on=None,
            fail_count=None,
            top=top,
            sort_by=sort_by,
            ignore_file=ignore_file,
            include_file=include_file,
        )
    except FileNotFoundError as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        return EXIT_INPUT_ERROR

    text_report = render_perf_summary_text(payload)

    if not text_output and not json_output:
        print("")
        print(text_report)
        print("")
        return EXIT_ANALYSIS_FOUND if payload["threshold_triggered"] else EXIT_SUCCESS

    if text_output:
        write_text_file(text_output, text_report)
        logger.info("Text baseline report exported to: %s", text_output)
        print(f"Text report exported to: {text_output}")

    if json_output:
        write_json_file(json_output, payload)
        logger.info("JSON baseline report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    return EXIT_ANALYSIS_FOUND if payload["threshold_triggered"] else EXIT_SUCCESS


def run_perf_compare(
    logger,
    path,
    baseline_path,
    text_output=None,
    json_output=None,
    config_path="explainable.toml",
    top=10,
    sort_by="severity",
    ignore_file=None,
    include_file=None,
):
    logger.info("Running performance comparison for project: %s", path)
    logger.info("Using baseline file: %s", baseline_path)

    try:
        baseline = load_json_file(baseline_path)
        current = build_perf_summary_payload(
            path=path,
            config_path=config_path,
            fail_on=None,
            fail_count=None,
            top=top,
            sort_by=sort_by,
            ignore_file=ignore_file,
            include_file=include_file,
        )
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


def run_baseline_create(logger, path, output, json_mode, config_path):
    logger.info("Creating finding baseline for path: %s", path)

    reports = scan_project(path, config_path=config_path)
    payload = build_baseline_payload(path, reports)
    save_baseline(payload, output)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Baseline created: {output}")
        print(f"Path: {payload['path']}")
        print(f"Finding count: {payload['finding_count']}")
        print("")

    return EXIT_SUCCESS


def run_baseline_compare(logger, path, baseline_path, viewer, json_mode, config_path):
    logger.info("Comparing current findings against baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    baseline_payload = load_baseline(baseline_path)
    regression_payload = build_regression_payload(
        path=path,
        current_reports=reports,
        baseline_payload=baseline_payload,
        viewer=viewer,
    )

    if json_mode:
        print(json.dumps(regression_payload, indent=2))
    else:
        print("")
        print(render_regression_text(regression_payload))
        print("")

    return EXIT_ANALYSIS_FOUND if regression_payload["regression_detected"] else EXIT_SUCCESS


def run_baseline_approve(logger, path, baseline_path, json_mode, config_path):
    logger.info("Approving current findings into baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    existing = load_baseline(baseline_path)
    payload = approve_current_findings(
        path=path,
        current_reports=reports,
        existing_baseline=existing,
    )
    save_baseline(payload, baseline_path)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Baseline approved: {baseline_path}")
        print(f"Path: {payload['path']}")
        print(f"Finding count: {payload['finding_count']}")
        print(f"Created at: {payload['created_at']}")
        print(f"Updated at: {payload['updated_at']}")
        print("")

    return EXIT_SUCCESS


def run_baseline_refresh(logger, path, baseline_path, json_mode, config_path):
    logger.info("Refreshing baseline from current project state: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    existing = load_baseline(baseline_path)
    payload = refresh_baseline_payload(
        path=path,
        current_reports=reports,
        existing_baseline=existing,
    )
    save_baseline(payload, baseline_path)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Baseline refreshed: {baseline_path}")
        print(f"Path: {payload['path']}")
        print(f"Finding count: {payload['finding_count']}")
        print(f"Created at: {payload['created_at']}")
        print(f"Updated at: {payload['updated_at']}")
        print("")

    return EXIT_SUCCESS


def run_baseline_prune(logger, path, baseline_path, json_mode, config_path):
    logger.info("Pruning resolved findings from baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    existing = load_baseline(baseline_path)
    payload = prune_baseline_payload(
        current_reports=reports,
        existing_baseline=existing,
    )
    save_baseline(payload, baseline_path)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Baseline pruned: {baseline_path}")
        print(f"Path: {payload['path']}")
        print(f"Finding count: {payload['finding_count']}")
        print(f"Created at: {payload['created_at']}")
        print(f"Updated at: {payload['updated_at']}")
        print("")

    return EXIT_SUCCESS


def run_triage_report(logger, path, baseline_path, viewer, json_mode, config_path):
    logger.info("Building triage report from baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    baseline_payload = load_baseline(baseline_path)
    regression_payload = build_regression_payload(
        path=path,
        current_reports=reports,
        baseline_payload=baseline_payload,
        viewer=viewer,
    )

    triage_items = build_triage_items(regression_payload)

    payload = {
        "path": path,
        "baseline_path": baseline_path,
        "triage_count": len(triage_items),
        "items": triage_items,
    }

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(render_triage_report_text(regression_payload))
        print("")

    return EXIT_ANALYSIS_FOUND if triage_items else EXIT_SUCCESS


def run_triage_create(logger, path, baseline_path, viewer, json_mode, config_path):
    logger.info("Creating triage tasks from baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    baseline_payload = load_baseline(baseline_path)
    regression_payload = build_regression_payload(
        path=path,
        current_reports=reports,
        baseline_payload=baseline_payload,
        viewer=viewer,
    )

    created = create_triage_tasks(regression_payload)

    payload = {
        "path": path,
        "baseline_path": baseline_path,
        "created_task_count": len(created),
        "created_tasks": created,
    }

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Triage tasks created: {len(created)}")
        for item in created:
            print(f"- {item['id']} | {item['title']}")
        print("")

    return EXIT_SUCCESS


def run_triage_sync(logger, path, baseline_path, viewer, json_mode, config_path):
    logger.info("Syncing triage tasks from baseline: %s", baseline_path)

    reports = scan_project(path, config_path=config_path)
    baseline_payload = load_baseline(baseline_path)
    regression_payload = build_regression_payload(
        path=path,
        current_reports=reports,
        baseline_payload=baseline_payload,
        viewer=viewer,
    )

    payload = sync_triage_tasks(regression_payload)

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(f"Created tasks: {payload['created_task_count']}")
        print(f"Marked done: {payload['marked_done_count']}")
        print(f"Kept open: {payload['kept_open_count']}")
        print("")

    return EXIT_SUCCESS


def run_history_snapshot(
    logger,
    path,
    baseline_path,
    history_path,
    viewer,
    json_mode,
    config_path,
):
    logger.info("Appending regression snapshot to history: %s", history_path)

    reports = scan_project(path, config_path=config_path)
    baseline_payload = load_baseline(baseline_path)
    regression_payload = build_regression_payload(
        path=path,
        current_reports=reports,
        baseline_payload=baseline_payload,
        viewer=viewer,
    )

    history_payload = load_history(history_path)
    updated_history = append_history_snapshot(
        history_payload,
        regression_payload=regression_payload,
    )
    save_history(updated_history, history_path)

    latest_snapshot = updated_history["snapshots"][-1]

    if json_mode:
        print(json.dumps(latest_snapshot, indent=2))
    else:
        print("")
        print(f"History snapshot saved: {history_path}")
        print(f"Timestamp: {latest_snapshot['timestamp']}")
        print(f"New findings: {latest_snapshot['new_finding_count']}")
        print(f"Resolved findings: {latest_snapshot['resolved_finding_count']}")
        print(f"Existing findings: {latest_snapshot['existing_finding_count']}")
        print("")

    return EXIT_SUCCESS


def run_trend_report(logger, history_path, json_mode):
    logger.info("Building trend report from history: %s", history_path)

    history_payload = load_history(history_path)
    report = build_trend_report(history_payload)

    if json_mode:
        print(json.dumps(report, indent=2))
    else:
        print("")
        print(render_trend_report_text(report))
        print("")

    return EXIT_SUCCESS


def run_doctor(
    logger,
    config_path: str,
    settings: dict,
    text_output=None,
    json_output=None,
    json_stdout: bool = False,
    strict_mode: bool = False,
):
    logger.info("Running setup doctor")

    payload = build_doctor_payload(
        config_path=config_path,
        settings=settings,
        strict_mode=strict_mode,
    )
    text_report = render_doctor_text(payload)

    if json_stdout or json_output == "STDOUT":
        print(json.dumps(payload, indent=2))
        return EXIT_ANALYSIS_FOUND if payload["overall_status"] in {"warn", "fail"} else EXIT_SUCCESS

    if json_output:
        write_json_file(json_output, payload)
        logger.info("JSON doctor report exported to: %s", json_output)
        print(f"JSON report exported to: {json_output}")

    if text_output:
        write_text_file(text_output, text_report)
        logger.info("Text doctor report exported to: %s", text_output)
        print(f"Text report exported to: {text_output}")

    if not text_output and not json_output:
        print("")
        print(text_report)
        print("")

    return EXIT_ANALYSIS_FOUND if payload["overall_status"] in {"warn", "fail"} else EXIT_SUCCESS


def run_check(logger, path, json_mode, config_path, settings, viewer="", baseline_path=None):
    logger.info("Running full project check: %s", path)

    doctor_payload = build_doctor_payload(
        config_path=config_path,
        settings=settings,
        strict_mode=False,
    )

    scan_reports = scan_project(path, config_path=config_path)

    resolved_top, resolved_sort_by, resolved_ignore_file, resolved_include_file = resolve_perf_options(
        settings=settings,
        top=None,
        sort_by=None,
        ignore_file=None,
        include_file=None,
    )

    perf_payload = build_perf_summary_payload(
        path=path,
        config_path=config_path,
        top=resolved_top,
        sort_by=resolved_sort_by,
        ignore_file=resolved_ignore_file,
        include_file=resolved_include_file,
    )
    perf_payload = enrich_perf_payload(perf_payload, viewer=viewer)

    payload = {
        "path": path,
        "doctor": doctor_payload,
        "scan": {
            "report_count": len(scan_reports),
            "reports": [enrich_report_context(report, viewer=viewer) for report in scan_reports],
        },
        "perf_summary": perf_payload,
    }

    regression_payload = None
    if baseline_path:
        baseline_payload = load_baseline(baseline_path)
        regression_payload = build_regression_payload(
            path=path,
            current_reports=scan_reports,
            baseline_payload=baseline_payload,
            viewer=viewer,
        )
        payload["regression"] = regression_payload

    if json_mode:
        print(json.dumps(payload, indent=2))
    else:
        print("")
        print(render_check_text(payload))
        print("")

    if doctor_payload["overall_status"] in {"warn", "fail"}:
        return EXIT_ANALYSIS_FOUND

    if regression_payload is not None:
        return EXIT_ANALYSIS_FOUND if regression_payload["regression_detected"] else EXIT_SUCCESS

    if len(scan_reports) > 0 or perf_payload["threshold_triggered"]:
        return EXIT_ANALYSIS_FOUND

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(run_cli())