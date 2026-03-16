from core.baseline import (
    build_baseline_payload,
    build_regression_payload,
    compare_findings,
)
from core.scanner import scan_python_file
from core.worklog import add_code_note, create_work_item


def test_compare_findings_detects_new_existing_and_resolved():
    baseline_findings = [
        {
            "id": "a1",
            "file_name": "core/scanner.py",
            "line": 10,
            "category": "performance",
            "severity": "medium",
            "message": "Old finding",
        },
        {
            "id": "a2",
            "file_name": "core/runtime_scanner.py",
            "line": 20,
            "category": "performance",
            "severity": "high",
            "message": "Resolved finding",
        },
    ]

    current_findings = [
        {
            "id": "a1",
            "file_name": "core/scanner.py",
            "line": 10,
            "category": "performance",
            "severity": "medium",
            "message": "Old finding",
        },
        {
            "id": "a3",
            "file_name": "core/bug_chain.py",
            "line": 30,
            "category": "performance",
            "severity": "high",
            "message": "New finding",
        },
    ]

    comparison = compare_findings(current_findings, baseline_findings)

    assert len(comparison["existing_findings"]) == 1
    assert len(comparison["new_findings"]) == 1
    assert len(comparison["resolved_findings"]) == 1
    assert comparison["new_findings"][0]["id"] == "a3"
    assert comparison["resolved_findings"][0]["id"] == "a2"


def test_build_regression_payload_includes_team_context(tmp_path, monkeypatch):
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

    create_work_item(
        task_id="TASK-1",
        title="Sample cleanup",
        primary_owner="Joseph",
        assignees=["Joseph"],
        files=["sample_target.py"],
    )

    add_code_note(
        note_id="NOTE-1",
        author="Joseph",
        body="Please review this nested loop @Alice",
        target_files=["sample_target.py"],
        target_lines=[{"file": "sample_target.py", "line": 3}],
    )

    report = scan_python_file(sample_file)
    baseline_payload = {
        "version": 1,
        "path": ".",
        "finding_count": 0,
        "findings": [],
    }

    payload = build_regression_payload(
        path=".",
        current_reports=[report],
        baseline_payload=baseline_payload,
        viewer="Alice",
    )

    assert payload["regression_detected"] is True
    assert payload["new_finding_count"] >= 1
    assert payload["new_findings"][0]["team_context"]["tasks"]


def test_build_baseline_payload_collects_findings(tmp_path):
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
    payload = build_baseline_payload(".", [report])

    assert payload["version"] == 1
    assert payload["finding_count"] >= 1
    assert payload["findings"]
