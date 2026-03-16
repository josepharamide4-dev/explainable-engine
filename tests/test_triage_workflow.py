from core.baseline import build_regression_payload
from core.scanner import scan_python_file
from core.triage import (
    build_triage_items,
    create_triage_tasks,
    sync_triage_tasks,
)
from core.worklog import get_all_work_items


def test_build_triage_items_suggests_owner_from_team_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    sample_file = tmp_path / "sample_target.py"
    sample_file.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    report = scan_python_file(sample_file)

    regression_payload = {
        "path": ".",
        "new_finding_count": 1,
        "new_findings": [
            {
                "id": "abc12345",
                "file_name": "sample_target.py",
                "line": 3,
                "severity": "high",
                "message": "Nested loop detected",
                "team_context": {
                    "people": {
                        "owners": ["Joseph"],
                        "watchers": ["Alice"],
                        "influencing_members": ["Bob"],
                    },
                    "tasks": [],
                    "notes": [],
                },
            }
        ],
    }

    items = build_triage_items(regression_payload)

    assert len(items) == 1
    assert items[0]["suggested_owner"] == "Joseph"


def test_create_triage_tasks_creates_one_task_per_new_regression(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    regression_payload = {
        "path": ".",
        "new_finding_count": 1,
        "new_findings": [
            {
                "id": "def67890",
                "file_name": "sample_target.py",
                "line": 5,
                "severity": "medium",
                "message": "Repeated expensive call",
                "team_context": {
                    "people": {
                        "owners": ["Joseph"],
                        "watchers": [],
                        "influencing_members": [],
                    },
                    "tasks": [],
                    "notes": [],
                },
            }
        ],
    }

    created = create_triage_tasks(regression_payload)
    items = get_all_work_items()

    assert len(created) == 1
    assert len(items) == 1
    assert items[0].finding_ids == ["def67890"]


def test_create_triage_tasks_does_not_duplicate_existing_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    regression_payload = {
        "path": ".",
        "new_finding_count": 1,
        "new_findings": [
            {
                "id": "same1234",
                "file_name": "sample_target.py",
                "line": 7,
                "severity": "high",
                "message": "Nested loop detected",
                "team_context": {
                    "people": {
                        "owners": ["Joseph"],
                        "watchers": [],
                        "influencing_members": [],
                    },
                    "tasks": [],
                    "notes": [],
                },
            }
        ],
    }

    first = create_triage_tasks(regression_payload)
    second = create_triage_tasks(regression_payload)
    items = get_all_work_items()

    assert len(first) == 1
    assert len(second) == 0
    assert len(items) == 1


def test_sync_triage_marks_resolved_tasks_done(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_triage_tasks(
        {
            "path": ".",
            "new_finding_count": 1,
            "new_findings": [
                {
                    "id": "resolved123",
                    "file_name": "sample_target.py",
                    "line": 9,
                    "severity": "high",
                    "message": "Old regression",
                    "team_context": {
                        "people": {
                            "owners": ["Joseph"],
                            "watchers": [],
                            "influencing_members": [],
                        },
                        "tasks": [],
                        "notes": [],
                    },
                }
            ],
        }
    )

    payload = sync_triage_tasks(
        {
            "new_findings": [],
            "existing_findings": [],
            "resolved_findings": [
                {
                    "id": "resolved123",
                    "file_name": "sample_target.py",
                    "line": 9,
                    "severity": "high",
                    "message": "Old regression",
                }
            ],
        }
    )

    items = get_all_work_items()

    assert payload["marked_done_count"] == 1
    assert items[0].status == "done"


def test_triage_with_real_regression_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    sample_file = tmp_path / "sample_target.py"
    sample_file.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    report = scan_python_file(sample_file)
    baseline_payload = {
        "version": 1,
        "path": ".",
        "finding_count": 0,
        "findings": [],
    }

    regression_payload = build_regression_payload(
        path=".",
        current_reports=[report],
        baseline_payload=baseline_payload,
        viewer="",
    )

    created = create_triage_tasks(regression_payload)
    assert created
