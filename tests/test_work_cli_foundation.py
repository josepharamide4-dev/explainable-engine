from types import SimpleNamespace

from core.work_cli import (
    run_member_add,
    run_note_add,
    run_note_show,
    run_work_add,
    run_work_assign,
    run_work_board,
    run_work_handover,
    run_work_update,
)


def test_run_member_add_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    args = SimpleNamespace(
        name="Alice",
        role="Engineer",
        inactive=False,
        influence_files="core/scanner.py",
        influence_findings="abc123",
        notes="Owns scanner work",
        json_mode=True,
    )

    rc = run_member_add(args)
    output = capsys.readouterr().out

    assert rc == 0
    assert '"name": "Alice"' in output
    assert '"role": "Engineer"' in output


def test_run_work_add_and_board(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    add_args = SimpleNamespace(
        id="TASK-100",
        title="Scanner cleanup",
        owner="Joseph",
        assignees="Alice,Bob",
        files="core/scanner.py",
        finding_ids="finding-1",
        notes="Reduce high severity",
        blockers="",
        collaborators="Charlie",
        watchers="Dana",
        json_mode=False,
    )

    rc = run_work_add(add_args)
    assert rc == 0

    board_args = SimpleNamespace(json_mode=False)
    rc = run_work_board(board_args)
    output = capsys.readouterr().out

    assert rc == 0
    assert "TASK-100" in output
    assert "Scanner cleanup" in output


def test_run_work_update(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    run_work_add(
        SimpleNamespace(
            id="TASK-101",
            title="Bug chain cleanup",
            owner="Joseph",
            assignees="",
            files="core/bug_chain.py",
            finding_ids="",
            notes="",
            blockers="",
            collaborators="",
            watchers="",
            json_mode=False,
        )
    )

    update_args = SimpleNamespace(
        id="TASK-101",
        title=None,
        status="in_progress",
        files=None,
        finding_ids=None,
        notes="Started work",
        blockers=None,
        collaborators=None,
        watchers=None,
        json_mode=True,
    )

    rc = run_work_update(update_args)
    output = capsys.readouterr().out

    assert rc == 0
    assert '"status": "in_progress"' in output


def test_run_work_assign_and_handover(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    run_work_add(
        SimpleNamespace(
            id="TASK-102",
            title="Runtime scanner task",
            owner="Joseph",
            assignees="",
            files="core/runtime_scanner.py",
            finding_ids="",
            notes="",
            blockers="",
            collaborators="",
            watchers="",
            json_mode=False,
        )
    )

    assign_args = SimpleNamespace(
        id="TASK-102",
        people="Alice,Bob",
        primary_owner="Alice",
        reason="Pairing",
        json_mode=True,
    )
    rc = run_work_assign(assign_args)
    output = capsys.readouterr().out
    assert rc == 0
    assert '"primary_owner": "Alice"' in output

    handover_args = SimpleNamespace(
        id="TASK-102",
        from_person="Alice",
        to_person="Bob",
        reason="Alice on leave",
        json_mode=True,
    )
    rc = run_work_handover(handover_args)
    output = capsys.readouterr().out
    assert rc == 0
    assert '"primary_owner": "Bob"' in output


def test_run_note_add_and_show(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    note_args = SimpleNamespace(
        id="NOTE-100",
        author="Joseph",
        body="Please check this loop @Alice",
        visibility="project",
        files="core/scanner.py",
        lines="core/scanner.py:152",
        finding_ids="finding-abc",
        task_ids="TASK-200",
        shared_with="Bob",
        tags="perf,handover",
        handover=False,
        json_mode=True,
    )

    rc = run_note_add(note_args)
    output = capsys.readouterr().out
    assert rc == 0
    assert '"id": "NOTE-100"' in output

    show_args = SimpleNamespace(
        file="core/scanner.py",
        line=152,
        finding_id="finding-abc",
        viewer="Alice",
        json_mode=False,
    )

    rc = run_note_show(show_args)
    output = capsys.readouterr().out
    assert rc == 0
    assert "NOTE-100" in output
    assert "Please check this loop" in output