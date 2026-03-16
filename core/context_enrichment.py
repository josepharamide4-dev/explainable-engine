from typing import Any, Dict, List
from pathlib import Path

from core.worklog import (
    find_notes_for_code,
    find_relevant_people_for_code,
    get_all_work_items,
)


def _normalize_path_variants(file_path: str) -> List[str]:
    if not file_path:
        return []

    raw = str(file_path).replace("\\", "/")
    variants = {raw}

    try:
        p = Path(file_path)
        variants.add(p.as_posix())
        variants.add(p.name)
        variants.add(str(p).replace("\\", "/"))
        if not p.is_absolute():
            try:
                variants.add(p.resolve().as_posix())
            except Exception:
                pass
    except Exception:
        pass

    return [item for item in variants if item]


def _path_matches(candidate: str, target: str) -> bool:
    candidate_variants = set(_normalize_path_variants(candidate))
    target_variants = set(_normalize_path_variants(target))

    if candidate_variants & target_variants:
        return True

    candidate_name = Path(candidate).name if candidate else ""
    target_name = Path(target).name if target else ""
    return bool(candidate_name and target_name and candidate_name == target_name)


def build_code_context(
    *,
    file_path: str,
    line_number: int = 0,
    finding_id: str = "",
    viewer: str = "",
) -> Dict[str, Any]:
    relevant_people = find_relevant_people_for_code(
        file_path=file_path,
        finding_id=finding_id,
    )

    notes = find_notes_for_code(
        file_path=file_path,
        line_number=line_number,
        finding_id=finding_id,
        viewer=viewer,
    )

    tasks = []
    for item in get_all_work_items():
        file_match = any(_path_matches(file_path, task_file) for task_file in item.files) if file_path else False
        finding_match = finding_id in item.finding_ids if finding_id else False

        if file_match or finding_match:
            tasks.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "primary_owner": item.primary_owner,
                    "assignees": list(item.assignees),
                    "files": list(item.files),
                    "finding_ids": list(item.finding_ids),
                    "linked_note_ids": list(item.linked_note_ids),
                }
            )

    return {
        "file_path": file_path,
        "line_number": line_number,
        "finding_id": finding_id,
        "people": relevant_people,
        "tasks": tasks,
        "notes": [note.to_dict() for note in notes],
    }


def enrich_perf_payload(payload: Dict[str, Any], viewer: str = "") -> Dict[str, Any]:
    enriched = dict(payload)
    enriched_top_files = []

    for item in payload.get("top_files", []):
        file_name = item["file_name"]
        context = build_code_context(
            file_path=file_name,
            viewer=viewer,
        )
        merged = dict(item)
        merged["team_context"] = context
        enriched_top_files.append(merged)

    enriched["top_files"] = enriched_top_files
    return enriched


def enrich_report_context(report, viewer: str = "") -> Dict[str, Any]:
    from dataclasses import asdict

    base = asdict(report)
    base["team_context"] = build_code_context(
        file_path=report.file_name,
        line_number=report.line_number,
        viewer=viewer,
    )

    findings_with_context: List[Dict[str, Any]] = []
    for finding in report.performance_scored_findings:
        finding_payload = dict(finding)
        finding_payload["team_context"] = build_code_context(
            file_path=report.file_name,
            line_number=finding.get("line", 0),
            finding_id=finding.get("id", ""),
            viewer=viewer,
        )
        findings_with_context.append(finding_payload)

    base["performance_scored_findings"] = findings_with_context
    return base


def render_team_context_text(context: Dict[str, Any]) -> str:
    lines: List[str] = []

    people = context.get("people", {})
    owners = people.get("owners", [])
    watchers = people.get("watchers", [])
    influencing = people.get("influencing_members", [])

    tasks = context.get("tasks", [])
    notes = context.get("notes", [])

    if owners or watchers or influencing or tasks or notes:
        lines.append("Team Context:")

    if owners:
        lines.append(f"- Owners: {', '.join(owners)}")
    if watchers:
        lines.append(f"- Watchers: {', '.join(watchers)}")
    if influencing:
        lines.append(f"- Influencing members: {', '.join(influencing)}")

    if tasks:
        lines.append("- Active work items:")
        for task in tasks:
            lines.append(
                f"  - {task['id']} | {task['title']} | "
                f"status={task['status']} | owner={task['primary_owner'] or '-'}"
            )

    if notes:
        lines.append("- Related notes:")
        for note in notes:
            lines.append(
                f"  - {note['id']} | author={note['author']} | {note['body']}"
            )

    return "\n".join(lines)
