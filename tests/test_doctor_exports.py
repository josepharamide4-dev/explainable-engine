import json
import subprocess
import sys
from pathlib import Path


def test_doctor_text_export(tmp_path: Path):
    text_report = tmp_path / "doctor.txt"

    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--text", str(text_report)],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert text_report.exists()

    content = text_report.read_text(encoding="utf-8")
    assert "Explainable Doctor Report:" in content
    assert "Checks:" in content


def test_doctor_json_export(tmp_path: Path):
    json_report = tmp_path / "doctor.json"

    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--json", str(json_report)],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert json_report.exists()

    data = json.loads(json_report.read_text(encoding="utf-8"))
    assert "config_path" in data
    assert "overall_status" in data
    assert "checks" in data


def test_doctor_json_stdout():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--json-stdout"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert "config_path" in data
    assert "checks" in data