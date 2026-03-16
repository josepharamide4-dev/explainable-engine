import json
import subprocess
import sys
from pathlib import Path


def test_perf_summary_uses_config_defaults(tmp_path: Path):
    config_file = tmp_path / "explainable.toml"
    config_file.write_text(
        """
[scan]
timeout = 2
ignore = ["venv", ".venv", "__pycache__", ".git"]

[report]
format = "text"
save_reports = false

[analysis]
detect_infinite_loops = true
detect_none_errors = true
detect_index_errors = true

[perf]
top = 3
sort_by = "file"
ignore_file = ""
include_file = ""
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--config",
            str(config_file),
            "perf-summary",
            ".",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    data = json.loads(result.stdout)
    assert data["top"] == 3
    assert data["sort_by"] == "file"


def test_perf_baseline_uses_config_defaults(tmp_path: Path):
    config_file = tmp_path / "explainable.toml"
    json_report = tmp_path / "baseline.json"

    config_file.write_text(
        """
[scan]
timeout = 2
ignore = ["venv", ".venv", "__pycache__", ".git"]

[report]
format = "text"
save_reports = false

[analysis]
detect_infinite_loops = true
detect_none_errors = true
detect_index_errors = true

[perf]
top = 2
sort_by = "findings"
ignore_file = ""
include_file = ""
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--config",
            str(config_file),
            "perf-baseline",
            ".",
            "--json",
            str(json_report),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    data = json.loads(json_report.read_text(encoding="utf-8"))
    assert data["top"] == 2
    assert data["sort_by"] == "findings"