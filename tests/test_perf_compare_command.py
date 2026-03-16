import json
import subprocess
import sys
from pathlib import Path


def test_perf_compare_json_output(tmp_path: Path):
    baseline_file = tmp_path / "baseline.json"

    baseline_result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--json"],
        capture_output=True,
        text=True,
    )
    assert baseline_result.returncode == 2
    baseline_file.write_text(baseline_result.stdout, encoding="utf-8")

    compare_result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-compare",
            ".",
            "--baseline",
            str(baseline_file),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert compare_result.returncode == 0
    data = json.loads(compare_result.stdout)
    assert "regression_detected" in data
    assert data["regression_detected"] is False
    assert "severity_delta" in data


def test_perf_compare_text_output(tmp_path: Path):
    baseline_file = tmp_path / "baseline.json"

    baseline_result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--json"],
        capture_output=True,
        text=True,
    )
    assert baseline_result.returncode == 2
    baseline_file.write_text(baseline_result.stdout, encoding="utf-8")

    compare_result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-compare",
            ".",
            "--baseline",
            str(baseline_file),
        ],
        capture_output=True,
        text=True,
    )

    assert compare_result.returncode == 0
    assert "Performance Baseline Comparison:" in compare_result.stdout
    assert "Regression detected: False" in compare_result.stdout