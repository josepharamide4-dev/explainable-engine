from core.scanner import scan_project


def test_scan_project_returns_reports():
    reports = scan_project(".")
    assert isinstance(reports, list)
    assert len(reports) > 0


def test_scan_project_contains_sample_target_report():
    reports = scan_project(".")
    file_names = [report.file_name for report in reports]

    assert any("sample_target.py" in name for name in file_names)