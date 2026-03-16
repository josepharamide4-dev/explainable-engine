import json
import subprocess
import sys
from pathlib import Path


def test_perf_summary_include_file_json(tmp_path: Path):
    include_file = tmp_path / ".explainableinclude"
    include_file.write_text("sample_target.py\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-summary",
            ".",
            "--include-file",
            str(include_file),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert data["include_file"] == str(include_file)
    assert "sample_target.py" in data["include_patterns"]


def test_perf_summary_include_and_ignore_files_json(tmp_path: Path):
    include_file = tmp_path / ".explainableinclude"
    ignore_file = tmp_path / ".explainableignore"

    include_file.write_text("sample_target.py\n", encoding="utf-8")
    ignore_file.write_text("sample_target.py\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "perf-summary",
            ".",
            "--include-file",
            str(include_file),
            "--ignore-file",
            str(ignore_file),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert data["total_files_scanned"] == 0