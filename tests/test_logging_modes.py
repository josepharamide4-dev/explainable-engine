import json
import subprocess
import sys


def test_quiet_json_mode_keeps_stdout_clean():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--quiet",
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


def test_verbose_json_mode_keeps_stdout_clean():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--verbose",
            "call-graph",
            "sample_target.py",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "call_graph" in data


def test_quiet_and_verbose_together_is_input_error():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--quiet",
            "--verbose",
            "list-functions",
            "sample_target.py",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "cannot be used together" in result.stdout