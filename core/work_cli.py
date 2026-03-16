import json
from typing import List

from core.worklog import (
    add_code_note,
    add_or_update_project_member,
    assign_people,
    build_work_board_payload,
    create_work_item,
    find_notes_for_code,
    handover_work_item,
    render_code_notes_text,
    render_work_board_text,
    update_work_item,
)


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_target_lines(value: str | None):
    """
    Accepts:
    core/scanner.py:152,core/bug_chain.py:77
    """
    if not value:
        return []

    result = []
    entries = [item.strip() for item in value.split(",") if item.strip()]
    for entry in entries:
        if ":" not in entry:
            continue
        file_part, line_part = entry.rsplit(":", 1)
        file_part = file_part.strip().replace("\\", "/")
        try:
            line_number = int(line_part.strip())
        except ValueError:
            continue

        if file_part and line_number > 0:
            result.append({"file": file_part, "line": line_number})

    return result


def run_member_add(args):
    member = add_or_update_project_member(
        name=args.name,
        role=args.role or "",
        active=not args.inactive,
        influence_files=_split_csv(args.influence_files),
        influence_finding_ids=_split_csv(args.influence_findings),
        notes=args.notes or "",
    )

    payload = {
        "status": "ok",
        "member": member.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nProject member saved:\n")
    print(f"Name: {member.name}")
    print(f"Role: {member.role or '-'}")
    print(f"Active: {member.active}")
    print(f"Influence files: {', '.join(member.influence_files) or '-'}")
    print(f"Influence findings: {', '.join(member.influence_finding_ids) or '-'}")
    print("")
    return 0


def run_work_add(args):
    item = create_work_item(
        task_id=args.id,
        title=args.title,
        primary_owner=args.owner or "",
        assignees=_split_csv(args.assignees),
        files=_split_csv(args.files),
        finding_ids=_split_csv(args.finding_ids),
        notes=args.notes or "",
        blockers=_split_csv(args.blockers),
        collaborators=_split_csv(args.collaborators),
        watchers=_split_csv(args.watchers),
    )

    payload = {
        "status": "ok",
        "task": item.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nWork item created:\n")
    print(f"ID: {item.id}")
    print(f"Title: {item.title}")
    print(f"Primary owner: {item.primary_owner or '-'}")
    print(f"Assignees: {', '.join(item.assignees) or '-'}")
    print("")
    return 0


def run_work_update(args):
    item = update_work_item(
        task_id=args.id,
        title=args.title,
        status=args.status,
        files=_split_csv(args.files) if args.files is not None else None,
        finding_ids=_split_csv(args.finding_ids) if args.finding_ids is not None else None,
        notes=args.notes,
        blockers=_split_csv(args.blockers) if args.blockers is not None else None,
        collaborators=_split_csv(args.collaborators) if args.collaborators is not None else None,
        watchers=_split_csv(args.watchers) if args.watchers is not None else None,
    )

    payload = {
        "status": "ok",
        "task": item.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nWork item updated:\n")
    print(f"ID: {item.id}")
    print(f"Status: {item.status}")
    print(f"Updated: {item.updated_at}")
    print("")
    return 0


def run_work_assign(args):
    item = assign_people(
        task_id=args.id,
        people=_split_csv(args.people),
        primary_owner=args.primary_owner or "",
        reason=args.reason or "",
    )

    payload = {
        "status": "ok",
        "task": item.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nPeople assigned:\n")
    print(f"ID: {item.id}")
    print(f"Primary owner: {item.primary_owner or '-'}")
    print(f"Assignees: {', '.join(item.assignees) or '-'}")
    print("")
    return 0


def run_work_handover(args):
    item = handover_work_item(
        task_id=args.id,
        from_person=args.from_person,
        to_person=args.to_person,
        reason=args.reason or "",
    )

    payload = {
        "status": "ok",
        "task": item.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nWork item handed over:\n")
    print(f"ID: {item.id}")
    print(f"Primary owner: {item.primary_owner or '-'}")
    print(f"Assignees: {', '.join(item.assignees) or '-'}")
    print("")
    return 0


def run_work_board(args):
    payload = build_work_board_payload()

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("")
    print(render_work_board_text(payload))
    print("")
    return 0


def run_note_add(args):
    note = add_code_note(
        note_id=args.id,
        author=args.author,
        body=args.body,
        visibility=args.visibility,
        target_files=_split_csv(args.files),
        target_lines=_parse_target_lines(args.lines),
        target_finding_ids=_split_csv(args.finding_ids),
        task_ids=_split_csv(args.task_ids),
        shared_with=_split_csv(args.shared_with),
        tags=_split_csv(args.tags),
        handover_note=args.handover,
    )

    payload = {
        "status": "ok",
        "note": note.to_dict(),
    }

    if args.json_mode:
        print(json.dumps(payload, indent=2))
        return 0

    print("\nCode note created:\n")
    print(f"ID: {note.id}")
    print(f"Author: {note.author}")
    print(f"Files: {', '.join(note.target_files) or '-'}")
    print(f"Finding IDs: {', '.join(note.target_finding_ids) or '-'}")
    print("")
    return 0


def run_note_show(args):
    notes = find_notes_for_code(
        file_path=args.file or "",
        line_number=args.line or 0,
        finding_id=args.finding_id or "",
        viewer=args.viewer or "",
    )

    if args.json_mode:
        print(json.dumps([note.to_dict() for note in notes], indent=2))
        return 0

    print("")
    print(render_code_notes_text(notes))
    print("")
    return 0