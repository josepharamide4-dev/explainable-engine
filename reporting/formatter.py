from reporting.models import AnalysisReport


def format_report(report: AnalysisReport) -> str:
    lines = [
        f"Title: {report.title}",
        f"Problem Type: {report.problem_type}",
        f"Severity: {report.severity}",
    ]

    if report.file_name or report.line_number or report.code_line:
        lines.extend(
            [
                "",
                "Failure Location:",
                f"File: {report.file_name or 'Unknown'}",
                f"Line: {report.line_number or 'Unknown'}",
                f"Code: {report.code_line or 'Unknown'}",
            ]
        )

    lines.extend(
        [
            "",
            "Explanation:",
            report.explanation or "No explanation available.",
            "",
            "Observed Facts:",
        ]
    )

    if report.observed_facts:
        for fact in report.observed_facts:
            lines.append(f"- {fact}")
    else:
        lines.append("- No observed facts recorded.")

    lines.extend(
        [
            "",
            "Suspected Cause:",
            report.suspected_cause or "No suspected cause available.",
            "",
            f"Confidence: {report.confidence}",
            "",
            "Suggested Next Action:",
            report.suggested_next_action or "No next action suggested.",
        ]
    )

    if report.root_cause_trace:
        lines.extend(["", "Root Cause Trace:"])
        for item in report.root_cause_trace:
            lines.append(f"- {item}")

    if report.call_trace:
        lines.extend(["", "Function Call Trace:"])
        for item in report.call_trace:
            lines.append(f"- {item}")

    if report.branch_trace:
        lines.extend(["", "Branch Trace:"])
        for item in report.branch_trace:
            lines.append(f"- {item}")

    if report.possible_solutions:
        lines.extend(["", "Possible Solutions:"])
        for solution in report.possible_solutions:
            lines.append(f"- {solution}")

    if report.recommended_solution:
        lines.extend(["", "Recommended Solution:", report.recommended_solution])

    if report.possible_risks:
        lines.extend(["", "Possible Risks:"])
        for risk in report.possible_risks:
            lines.append(f"- {risk}")

    if report.risk_level:
        lines.extend(["", f"Risk Level: {report.risk_level}"])

    if report.verification_status:
        lines.extend(["", f"Verification Status: {report.verification_status}"])

    if report.verification_notes:
        lines.extend(["", "Verification Notes:"])
        for note in report.verification_notes:
            lines.append(f"- {note}")

    if report.fix_verification_status:
        lines.extend(["", f"Fix Verification Status: {report.fix_verification_status}"])

    if report.fix_verification_notes:
        lines.extend(["", "Fix Verification Notes:"])
        for note in report.fix_verification_notes:
            lines.append(f"- {note}")

    if report.version_comparison_status:
        lines.extend(["", f"Version Comparison Status: {report.version_comparison_status}"])

    if report.version_comparison_notes:
        lines.extend(["", "Version Comparison Notes:"])
        for note in report.version_comparison_notes:
            lines.append(f"- {note}")

    if report.optimization_status:
        lines.extend(["", f"Optimization Status: {report.optimization_status}"])

    if report.optimization_notes:
        lines.extend(["", "Optimization Notes:"])
        for note in report.optimization_notes:
            lines.append(f"- {note}")

    if report.performance_overall_severity:
        lines.extend(["", f"Performance Overall Severity: {report.performance_overall_severity}"])

    if report.performance_severity_summary:
        summary = report.performance_severity_summary
        lines.extend(
            [
                "",
                "Performance Severity Summary:",
                f"- high={summary.get('high', 0)}",
                f"- medium={summary.get('medium', 0)}",
                f"- low={summary.get('low', 0)}",
            ]
        )

    if report.inspection_findings:
        lines.extend(["", "Code Inspection Findings:"])
        for finding in report.inspection_findings:
            lines.append(f"- {finding}")

    if report.bug_risks:
        lines.extend(["", "Potential Bug Risks:"])
        for risk in report.bug_risks:
            lines.append(f"- {risk}")

    if report.notes:
        lines.extend(["", "Notes:"])
        for note in report.notes:
            lines.append(f"- {note}")

    return "\n".join(lines)