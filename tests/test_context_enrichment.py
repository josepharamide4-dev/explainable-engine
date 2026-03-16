from core.context_enrichment import (
    build_code_context,
    enrich_perf_payload,
    render_team_context_text,
)
from core.worklog import add_code_note, add_or_update_project_member, create_work_item


def test_build_code_context_includes_people_tasks_and_notes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    add_or_update_project_member(
        name="Alice",
        role="Engineer",
        influence_files=["core/scanner.py"],
    )

    create_work_item(
        task_id="TASK-1",
        title="Scanner cleanup",
        primary_owner="Joseph",
        assignees=["Joseph"],
        files=["core/scanner.py"],
    )

    add_code_note(
        note_id="NOTE-1",
        author="Joseph",
        body="Please review this loop @Alice",
        target_files=["core/scanner.py"],
        target_lines=[{"file": "core/scanner.py", "line": 152}],
    )

    context = build_code_context(
        file_path="core/scanner.py",
        line_number=152,
        viewer="Alice",
    )

    assert "Alice" in context["people"]["influencing_members"]
    assert len(context["tasks"]) == 1
    assert len(context["notes"]) == 1
    assert context["notes"][0]["id"] == "NOTE-1"


def test_enrich_perf_payload_adds_team_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_work_item(
        task_id="TASK-2",
        title="Runtime scanner cleanup",
        primary_owner="Joseph",
        assignees=["Joseph"],
        files=["core/runtime_scanner.py"],
    )

    payload = {
        "path": ".",
        "top_files": [
            {
                "file_name": "core/runtime_scanner.py",
                "overall_severity": "high",
                "finding_count": 5,
                "severity_summary": {"high": 1, "medium": 3, "low": 1},
            }
        ],
    }

    enriched = enrich_perf_payload(payload)
    assert "team_context" in enriched["top_files"][0]
    assert len(enriched["top_files"][0]["team_context"]["tasks"]) == 1


def test_render_team_context_text_outputs_details():
    context = {
        "people": {
            "owners": ["Joseph"],
            "watchers": ["Alice"],
            "influencing_members": ["Bob"],
        },
        "tasks": [
            {
                "id": "TASK-3",
                "title": "Bug chain cleanup",
                "status": "in_progress",
                "primary_owner": "Joseph",
            }
        ],
        "notes": [
            {
                "id": "NOTE-9",
                "author": "Joseph",
                "body": "Check this issue",
            }
        ],
    }

    text = render_team_context_text(context)

    assert "Owners: Joseph" in text
    assert "Watchers: Alice" in text
    assert "Influencing members: Bob" in text
    assert "TASK-3" in text
    assert "NOTE-9" in text
