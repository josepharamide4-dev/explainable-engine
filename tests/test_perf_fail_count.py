import json
import subprocess
import sys


def test_perf_fail_count_can_suppress_failure():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py", "--fail-on", "high", "--fail-count", "10"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Threshold triggered: False" in result.stdout


def test_perf_fail_count_can_trigger_failure():
    result = subprocess.run(
        [sys.executable, "main.py", "perf", "sample_target.py", "--fail-on", "low", "--fail-count", "1"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Threshold triggered: True" in result.stdout


def test_perf_summary_json_fail_count_output():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--fail-on", "low", "--fail-count", "1", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    assert data["fail_on"] == "low"
    assert data["fail_count"] == 1
    assert data["qualifying_finding_count"] >= 1
    assert data["threshold_triggered"] is True