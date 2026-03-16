import json
import subprocess
import sys


def test_analyze_file_json_is_clean_stdout():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "analyze-file",
            "sample_target.py",
            "--function",
            "checkout",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["status"] == "runtime_issue_found"
    assert result.stderr.strip() != ""


def test_scan_json_is_clean_stdout():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "scan",
            ".",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert "reports" in data
    assert result.stderr.strip() != ""


def test_trace_json_is_clean_stdout():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "trace",
            ".",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert "reports" in data
    assert result.stderr.strip() != ""