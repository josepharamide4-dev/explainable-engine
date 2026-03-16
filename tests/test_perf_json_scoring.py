import json
import subprocess
import sys

from core.scanner import scan_python_file


def test_perf_report_contains_structured_scoring_fields():
    report = scan_python_file("sample_target.py")

    assert report.performance_overall_severity == "high"
    assert report.performance_severity_summary["high"] >= 1
    assert isinstance(report.performance_scored_findings, list)
    assert len(report.performance_scored_findings) > 0


def test_perf_json_output_contains_scoring_fields():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    report = data["report"]

    assert report["performance_overall_severity"] == "high"
    assert "performance_severity_summary" in report
    assert "performance_scored_findings" in report
    assert isinstance(report["performance_scored_findings"], list)
    assert len(report["performance_scored_findings"]) > 0