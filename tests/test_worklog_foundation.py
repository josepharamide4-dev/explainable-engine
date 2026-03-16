from core.worklog import (
    add_code_note,
    add_or_update_project_member,
    build_work_board_payload,
    create_work_item,
    find_notes_for_code,
    find_relevant_people_for_code,
    get_note,
    handover_work_item,
    render_code_notes_text,
    update_work_item,
)


def test_create_work_item_with_multiple_assignees(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    item = create_work_item(
        task_id="TASK-001",
        title="Optimize runtime scanner",
        primary_owner="Joseph",
        assignees=["Joseph", "Alice", "Alice"],
        files=["core/runtime_scanner.py"],
        finding_ids=["abc123"],
        collaborators=["Bob"],
        watchers=["Charlie"],
        path=str(worklog_path),
    )

    assert item.primary_owner == "Joseph"
    assert item.assignees == ["Joseph", "Alice"]
    assert item.files == ["core/runtime_scanner.py"]
    assert item.finding_ids == ["abc123"]
    assert item.collaborators == ["Bob"]
    assert item.watchers == ["Charlie"]


def test_handover_updates_primary_owner_and_history(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    create_work_item(
        task_id="TASK-002",
        title="Reduce scanner severity",
        primary_owner="Joseph",
        assignees=["Joseph", "Alice"],
        path=str(worklog_path),
    )

    item = handover_work_item(
        task_id="TASK-002",
        from_person="Joseph",
        to_person="Bob",
        reason="Joseph on leave",
        path=str(worklog_path),
    )

    assert item.primary_owner == "Bob"
    assert "Bob" in item.assignees
    assert "Joseph" not in item.assignees
    assert any(event.action == "handover" for event in item.assignment_history)


def test_update_work_item_status_sets_started_and_completed(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    create_work_item(
        task_id="TASK-003",
        title="Fix bug chain issue",
        primary_owner="Alice",
        path=str(worklog_path),
    )

    item = update_work_item(
        "TASK-003",
        status="in_progress",
        path=str(worklog_path),
    )
    assert item.started_at

    item = update_work_item(
        "TASK-003",
        status="done",
        path=str(worklog_path),
    )
    assert item.completed_at


def test_build_work_board_payload_groups_tasks(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    create_work_item(
        task_id="TASK-004",
        title="Task one",
        primary_owner="Alice",
        path=str(worklog_path),
    )
    create_work_item(
        task_id="TASK-005",
        title="Task two",
        primary_owner="Bob",
        path=str(worklog_path),
    )

    update_work_item("TASK-005", status="in_progress", path=str(worklog_path))

    payload = build_work_board_payload(str(worklog_path))

    assert payload["task_count"] == 2
    assert len(payload["statuses"]["todo"]) == 1
    assert len(payload["statuses"]["in_progress"]) == 1


def test_code_note_links_to_code_and_mentions_people(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    note = add_code_note(
        note_id="NOTE-001",
        author="Joseph",
        body="Please review this loop @Alice @Bob",
        target_files=["core/runtime_scanner.py"],
        target_lines=[{"file": "core/runtime_scanner.py", "line": 152}],
        target_finding_ids=["finding-123"],
        shared_with=["Charlie"],
        tags=["perf", "handover"],
        path=str(worklog_path),
    )

    assert note.mentions == ["Alice", "Bob"]
    assert note.target_files == ["core/runtime_scanner.py"]
    assert note.target_lines == [{"file": "core/runtime_scanner.py", "line": 152}]
    assert note.target_finding_ids == ["finding-123"]
    assert note.shared_with == ["Charlie"]


def test_find_notes_for_code_respects_visibility_and_targets(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    add_code_note(
        note_id="NOTE-002",
        author="Joseph",
        body="Project-wide note on this code @Alice",
        visibility="project",
        target_files=["core/scanner.py"],
        target_finding_ids=["finding-456"],
        path=str(worklog_path),
    )

    notes = find_notes_for_code(
        file_path="core/scanner.py",
        finding_id="finding-456",
        viewer="Alice",
        path=str(worklog_path),
    )

    assert len(notes) == 1
    assert notes[0].id == "NOTE-002"


def test_find_relevant_people_for_code_uses_members_and_tasks(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    add_or_update_project_member(
        name="Alice",
        role="Engineer",
        influence_files=["core/scanner.py"],
        path=str(worklog_path),
    )

    create_work_item(
        task_id="TASK-006",
        title="Scanner cleanup",
        primary_owner="Bob",
        assignees=["Bob"],
        files=["core/scanner.py"],
        watchers=["Charlie"],
        path=str(worklog_path),
    )

    result = find_relevant_people_for_code(
        file_path="core/scanner.py",
        path=str(worklog_path),
    )

    assert "Alice" in result["influencing_members"]
    assert "Bob" in result["owners"]
    assert "Charlie" in result["watchers"]


def test_render_code_notes_text_outputs_note_content(tmp_path):
    worklog_path = tmp_path / ".explainable-worklog.json"

    add_code_note(
        note_id="NOTE-003",
        author="Joseph",
        body="Handover note for @Alice",
        handover_note=True,
        target_files=["core/bug_chain.py"],
        path=str(worklog_path),
    )

    note = get_note("NOTE-003", str(worklog_path))
    text = render_code_notes_text([note])

    assert "NOTE-003" in text
    assert "core/bug_chain.py" in text
    assert "Handover note for @Alice" in text