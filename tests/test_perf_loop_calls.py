from core.scanner import scan_python_file


def test_perf_detects_function_calls_inside_loops():
    report = scan_python_file("sample_target.py")

    findings_text = "\n".join(report.inspection_findings)

    assert "Function call `expensive_lookup()` detected inside a loop" in findings_text


def test_perf_still_detects_nested_loops():
    report = scan_python_file("sample_target.py")

    findings_text = "\n".join(report.inspection_findings)

    assert "Nested loop detected" in findings_text