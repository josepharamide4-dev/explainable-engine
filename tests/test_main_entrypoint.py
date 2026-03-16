import subprocess
import sys


def test_main_help_runs():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Explainable - Python debugging and optimization assistant" in result.stdout


def test_main_doctor_runs():
    result = subprocess.run(
        [sys.executable, "main.py", "doctor"],
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2)
    assert result.stdout.strip() != ""


def test_main_work_board_runs():
    result = subprocess.run(
        [sys.executable, "main.py", "work-board"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Explainable Work Board" in result.stdout


def test_main_incremental_state_init_runs(tmp_path):
    state_path = tmp_path / ".scanstate.json"
    demo = tmp_path / "demo.py"
    demo.write_text("print('demo')\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "incremental-state-init",
            str(tmp_path),
            "--state",
            str(state_path),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert state_path.exists()
    assert '"file_count": 1' in result.stdout


def test_main_incremental_scan_runs(tmp_path):
    state_path = tmp_path / ".scanstate.json"
    demo = tmp_path / "demo.py"
    demo.write_text("print('demo')\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "main.py",
            "incremental-state-init",
            str(tmp_path),
            "--state",
            str(state_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    demo.write_text(
        """
def demo():
    items = [1, 2]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "incremental-scan",
            str(tmp_path),
            "--state",
            str(state_path),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert '"changed_files"' in result.stdout