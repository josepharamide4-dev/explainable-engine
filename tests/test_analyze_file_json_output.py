import json
import subprocess
import sys


def test_analyze_file_json_output_for_failing_function():
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
    assert data["file"] == "sample_target.py"
    assert data["function"] == "checkout"
    assert data["status"] == "runtime_issue_found"
    assert data["report"]["problem_type"] == "TypeError"


def test_analyze_file_json_output_for_healthy_function():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "analyze-file",
            "sample_target.py",
            "--function",
            "healthy_function",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert data["file"] == "sample_target.py"
    assert data["function"] == "healthy_function"
    assert data["status"] == "no_runtime_error"
    assert data["report"] is None


def test_analyze_file_json_output_for_missing_function():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "analyze-file",
            "sample_target.py",
            "--function",
            "does_not_exist",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    data = json.loads(result.stdout)
    assert "error" in data
    assert data["error"]["type"] == "AttributeError"