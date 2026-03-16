import json
import subprocess
import sys
from pathlib import Path


def test_perf_baseline_json_export(tmp_path: Path):
    json_report = tmp_path / "baseline.json"

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-baseline",
            ".",
            "--json",
            str(json_report),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert json_report.exists()

    data = json.loads(json_report.read_text(encoding="utf-8"))
    assert data["path"] == "."
    assert "top_files" in data


def test_perf_baseline_text_export(tmp_path: Path):
    text_report = tmp_path / "baseline.txt"

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-baseline",
            ".",
            "--text",
            str(text_report),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert text_report.exists()

    content = text_report.read_text(encoding="utf-8")
    assert "Performance Summary:" in content
    assert "Top files by severity:" in content