import json
import subprocess
import sys
from pathlib import Path


def test_perf_summary_ignore_file_json(tmp_path: Path):
    ignore_file = tmp_path / ".explainableignore"
    ignore_file.write_text("sample_target.py\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-summary",
            ".",
            "--ignore-file",
            str(ignore_file),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert data["ignore_file"] == str(ignore_file)
    assert "sample_target.py" in data["ignore_patterns"]


def test_perf_compare_ignore_file_text(tmp_path: Path):
    baseline_file = tmp_path / "baseline.json"
    ignore_file = tmp_path / ".explainableignore"

    baseline_result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--json"],
        capture_output=True,
        text=True,
    )
    assert baseline_result.returncode == 2
    baseline_file.write_text(baseline_result.stdout, encoding="utf-8")

    ignore_file.write_text("sample_target.py\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-compare",
            ".",
            "--baseline",
            str(baseline_file),
            "--ignore-file",
            str(ignore_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2, 1)