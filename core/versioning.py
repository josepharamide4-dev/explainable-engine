from reporting.models import AnalysisReport


def compare_versions(
    report: AnalysisReport,
    broken_func,
    working_func,
) -> AnalysisReport:
    broken_failed = False
    broken_result = None
    broken_error = None

    working_failed = False
    working_result = None
    working_error = None

    try:
        broken_result = broken_func()
    except Exception as exc:
        broken_failed = True
        broken_error = f"{type(exc).__name__}: {exc}"

    try:
        working_result = working_func()
    except Exception as exc:
        working_failed = True
        working_error = f"{type(exc).__name__}: {exc}"

    if broken_failed and not working_failed:
        report.version_comparison_status = "behavior changed across versions"
        report.version_comparison_notes = [
            "The current or broken version failed during execution.",
            "The comparison or working version completed successfully.",
            f"Broken version error: {broken_error}",
            f"Working version result: {working_result!r}",
        ]
        return report

    if broken_failed and working_failed:
        report.version_comparison_status = "both versions failed"
        report.version_comparison_notes = [
            f"Broken version error: {broken_error}",
            f"Working version error: {working_error}",
            "This suggests the issue may not be a new regression, or both versions are affected.",
        ]
        return report

    if not broken_failed and not working_failed:
        if broken_result != working_result:
            report.version_comparison_status = "output changed across versions"
            report.version_comparison_notes = [
                f"Broken version result: {broken_result!r}",
                f"Working version result: {working_result!r}",
                "Both versions completed successfully, but the outputs differ.",
            ]
        else:
            report.version_comparison_status = "no visible behavior change"
            report.version_comparison_notes = [
                f"Broken version result: {broken_result!r}",
                f"Working version result: {working_result!r}",
                "Both versions completed successfully and produced the same output.",
            ]
        return report

    report.version_comparison_status = "inconclusive"
    report.version_comparison_notes = [
        "The version comparison did not produce a clear result.",
    ]
    return report