from core.scanner import scan_python_file


def test_perf_findings_include_severity_labels():
    report = scan_python_file("sample_target.py")
    findings_text = "\n".join(report.inspection_findings)

    assert "[HIGH]" in findings_text
    assert "[MEDIUM]" in findings_text
    assert "[LOW]" in findings_text


def test_perf_optimization_status_mentions_overall_severity():
    report = scan_python_file("sample_target.py")

    assert "severity" in report.optimization_status
    assert "high severity" in report.optimization_status


def test_perf_optimization_notes_include_severity_summary():
    report = scan_python_file("sample_target.py")
    notes_text = "\n".join(report.optimization_notes)

    assert "Severity summary:" in notes_text
    assert "high=" in notes_text
    assert "medium=" in notes_text
    assert "low=" in notes_text