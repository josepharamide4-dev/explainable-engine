import json
import subprocess
import sys
from pathlib import Path


def test_doctor_json_includes_fix_hint_field():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0
    assert "fix_hint" in data["checks"][0]


def test_doctor_text_shows_fix_hint_for_missing_include_file(tmp_path: Path):
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
        [sys.executable, "main.py", "--config", str(config_file), "doctor"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Fix:" in result.stdout
    assert "missing.include" in result.stdout