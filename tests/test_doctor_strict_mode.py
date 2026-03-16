import json
import subprocess
import sys
from pathlib import Path


def test_doctor_json_includes_strict_mode_flag():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--strict", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert data["strict_mode"] is True


def test_doctor_text_shows_strict_mode(tmp_path: Path):
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
top = 5
sort_by = "severity"
ignore_file = ""
include_file = "missing.include"
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "main.py", "--config", str(config_file), "doctor", "--strict"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Strict mode: True" in result.stdout