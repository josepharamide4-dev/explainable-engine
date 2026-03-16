import json
import subprocess
import sys


def test_perf_command_text_output():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Performance Heuristic Report:" in result.stdout
    assert "sample_target.py" in result.stdout


def test_perf_command_json_output():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    assert data["file"] == "sample_target.py"
    assert "report" in data
    assert data["report"]["file_name"].endswith("sample_target.py")