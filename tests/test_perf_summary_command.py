import json
import subprocess
import sys


def test_perf_summary_text_output():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", "."],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Performance Summary:" in result.stdout
    assert "Total files scanned:" in result.stdout
    assert "Top files by severity:" in result.stdout


def test_perf_summary_json_output():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    assert data["path"] == "."
    assert "total_files_scanned" in data
    assert "files_with_findings" in data
    assert "total_severity_summary" in data
    assert "top_files" in data
    assert isinstance(data["top_files"], list)