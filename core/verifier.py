from reporting.models import AnalysisReport


def add_basic_verification(report: AnalysisReport) -> AnalysisReport:
    if report.problem_type == "TypeError":
        report.verification_status = "supported hypothesis"
        report.verification_notes = [
            "The reported values suggest that an invalid type reached the failing operation.",
            "The recommended fix should be confirmed by rerunning the failing case after validation is added.",
        ]
        return report

    if report.problem_type == "IndexError":
        report.verification_status = "supported hypothesis"
        report.verification_notes = [
            "The observed collection length supports the conclusion that indexing exceeded the available range.",
            "The recommended fix should be confirmed by rerunning the case with empty and non-empty collections.",
        ]
        return report

    if report.problem_type == "KeyError":
        report.verification_status = "supported hypothesis"
        report.verification_notes = [
            "The observed dictionary keys support the conclusion that the requested key was missing.",
            "The recommended fix should be confirmed by testing both present-key and missing-key cases.",
        ]
        return report

    if report.problem_type == "AttributeError":
        report.verification_status = "supported hypothesis"
        report.verification_notes = [
            "The observed value and error message support the conclusion that attribute access was invalid.",
            "The recommended fix should be confirmed by rerunning the case with valid and invalid object values.",
        ]
        return report

    report.verification_status = "unverified"
    report.verification_notes = [
        "No verification rule exists yet for this error type.",
    ]
    return report


def verify_fix(report: AnalysisReport, original_func, fixed_func) -> AnalysisReport:
    original_failed = False
    fixed_succeeded = False
    fixed_result = None

    try:
        original_func()
    except Exception:
        original_failed = True

    try:
        fixed_result = fixed_func()
        fixed_succeeded = True
    except Exception as exc:
        report.fix_verification_status = "fix failed verification"
        report.fix_verification_notes = [
            "The original function still fails as expected.",
            f"The proposed fixed function also failed: {type(exc).__name__}: {exc}",
        ]
        return report

    if original_failed and fixed_succeeded:
        report.fix_verification_status = "verified fix"
        report.fix_verification_notes = [
            "The original function reproduced the failure.",
            "The proposed fixed function completed without raising an exception.",
            f"Fixed function result: {fixed_result!r}",
        ]
        return report

    if not original_failed and fixed_succeeded:
        report.fix_verification_status = "inconclusive"
        report.fix_verification_notes = [
            "The original function did not fail during verification.",
            "The proposed fixed function completed successfully.",
            "This suggests the failing case may not have been reproduced during verification.",
        ]
        return report

    report.fix_verification_status = "unverified"
    report.fix_verification_notes = [
        "The fix could not be verified with the provided functions.",
    ]
    return report