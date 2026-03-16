import json
import subprocess
import sys


def test_perf_fail_on_high_triggers_for_sample_target():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py", "--fail-on", "high"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Threshold triggered: True" in result.stdout


def test_perf_summary_fail_on_high_triggers():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--fail-on", "high"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Fail threshold: high" in result.stdout
    assert "Threshold triggered: True" in result.stdout


def test_perf_summary_json_fail_threshold():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--fail-on", "high", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    assert data["fail_on"] == "high"
    assert data["threshold_triggered"] is True
    assert data["highest_severity_found"] == "high"