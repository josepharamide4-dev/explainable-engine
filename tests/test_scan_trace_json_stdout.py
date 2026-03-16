import json
import subprocess
import sys


def test_scan_json_stdout():
    result = subprocess.run(
        [sys.executable, "main.py", "scan", ".", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["path"] == "."
    assert "report_count" in data
    assert isinstance(data["reports"], list)


def test_trace_json_stdout():
    result = subprocess.run(
        [sys.executable, "main.py", "trace", ".", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["path"] == "."
    assert "report_count" in data
    assert isinstance(data["reports"], list)