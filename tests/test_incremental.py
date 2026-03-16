import json
import subprocess
import sys

from core.incremental import (
    build_scan_state,
    compare_states,
    incremental_scan,
    load_state,
    save_state,
)


def test_build_scan_state(tmp_path):
    file_path = tmp_path / "a.py"
    file_path.write_text("print('a')\n", encoding="utf-8")

    payload = build_scan_state(str(tmp_path))

    assert payload["version"] == 1
    assert payload["file_count"] == 1
    assert payload["files"][0]["path"] == "a.py"
    assert payload["files"][0]["hash"]


def test_compare_states_detects_changed_file(tmp_path):
    file_path = tmp_path / "a.py"
    file_path.write_text("print('a')\n", encoding="utf-8")

    old_state = build_scan_state(str(tmp_path))

    file_path.write_text("print('changed')\n", encoding="utf-8")
    new_state = build_scan_state(str(tmp_path))

    diff = compare_states(old_state, new_state)

    assert diff["changed"] == ["a.py"]
    assert diff["added"] == []
    assert diff["removed"] == []


def test_save_and_load_state(tmp_path):
    state_path = tmp_path / ".scanstate.json"

    file_path = tmp_path / "a.py"
    file_path.write_text("print('a')\n", encoding="utf-8")

    payload = build_scan_state(str(tmp_path))
    save_state(payload, str(state_path))

    loaded = load_state(str(state_path))

    assert loaded["version"] == 1
    assert loaded["file_count"] == 1
    assert loaded["files"][0]["path"] == "a.py"


def test_incremental_scan_first_run_scans_all_python_files(tmp_path):
    state_path = tmp_path / ".scanstate.json"

    a_file = tmp_path / "a.py"
    b_file = tmp_path / "b.py"

    a_file.write_text("print('a')\n", encoding="utf-8")
    b_file.write_text("print('b')\n", encoding="utf-8")

    payload = incremental_scan(project_path=str(tmp_path), state_path=str(state_path))

    assert payload["previous_state_found"] is False
    assert sorted(payload["changed_files"]) == ["a.py", "b.py"]
    assert payload["removed_files"] == []
    assert len(payload["reports"]) == 2


def test_incremental_scan_detects_changed_file(tmp_path):
    state_path = tmp_path / ".scanstate.json"

    file_path = tmp_path / "a.py"
    file_path.write_text(
        """
def alpha():
    return 1
""".strip(),
        encoding="utf-8",
    )

    initial_state = build_scan_state(str(tmp_path))
    save_state(initial_state, str(state_path))

    file_path.write_text(
        """
def alpha():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    payload = incremental_scan(project_path=str(tmp_path), state_path=str(state_path))

    assert payload["previous_state_found"] is True
    assert payload["changed_files"] == ["a.py"]
    assert payload["removed_files"] == []
    assert len(payload["reports"]) == 1


def test_incremental_state_init_command_outputs_json(tmp_path):
    state_path = tmp_path / ".scanstate.json"
    file_path = tmp_path / "demo.py"
    file_path.write_text("print('demo')\n", encoding="utf-8")

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

    payload = json.loads(result.stdout)
    assert payload["file_count"] == 1
    assert state_path.exists()


def test_incremental_scan_command_outputs_json(tmp_path):
    state_path = tmp_path / ".scanstate.json"
    file_path = tmp_path / "demo.py"
    file_path.write_text("print('demo')\n", encoding="utf-8")

    initial_state = build_scan_state(str(tmp_path))
    save_state(initial_state, str(state_path))

    file_path.write_text(
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

    payload = json.loads(result.stdout)
    assert payload["changed_files"] == ["demo.py"]
    assert payload["removed_files"] == []
    assert len(payload["reports"]) == 1