import json
import subprocess
import sys


def test_doctor_text_output():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert "Explainable Doctor Report:" in result.stdout
    assert "Overall status:" in result.stdout
    assert "Checks:" in result.stdout


def test_doctor_json_output():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)

    data = json.loads(result.stdout)
    assert "config_path" in data
    assert "overall_status" in data
    assert "check_count" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0