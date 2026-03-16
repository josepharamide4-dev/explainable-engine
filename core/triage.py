from typing import Any, Dict, List

from core.worklog import (
    create_work_item,
    get_all_work_items,
    update_work_item,
)


def _suggest_owner(team_context: Dict[str, Any]) -> str:
    people = team_context.get("people", {})
    owners = people.get("owners", [])
    influencing = people.get("influencing_members", [])
    watchers = people.get("watchers", [])

    if owners:
        return owners[0]
    if influencing:
        return influencing[0]
    if watchers:
        return watchers[0]
    return ""


def _existing_task_for_finding(finding_id: str):
    for item in get_all_work_items():
        if finding_id in item.finding_ids:
            return item
    return None


def _make_task_id(finding_id: str) -> str:
    return f"TRIAGE-{finding_id[:8].upper()}"


def _make_task_title(finding: Dict[str, Any]) -> str:
    return f"Fix regression in {finding['file_name']} line {finding['line']}"


def build_triage_items(regression_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for finding in regression_payload.get("new_findings", []):
        finding_id = finding.get("id", "")
        team_context = finding.get("team_context", {})
        existing_task = _existing_task_for_finding(finding_id)

        items.append(
            {
                "finding_id": finding_id,
                "file_name": finding.get("file_name", ""),
                "line": finding.get("line", 0),
                "severity": finding.get("severity", ""),
                "message": finding.get("message", ""),
                "suggested_owner": _suggest_owner(team_context),
                "existing_task_id": existing_task.id if existing_task else "",
                "existing_task_status": existing_task.status if existing_task else "",
                "team_context": team_context,
            }
        )

    return items


def render_triage_report_text(regression_payload: Dict[str, Any]) -> str:
    triage_items = build_triage_items(regression_payload)

    lines = [
        "Explainable Triage Report:",
        "",
        f"Path: {regression_payload.get('path', '')}",
        f"New regressions: {regression_payload.get('new_finding_count', 0)}",
        "",
    ]

    if not triage_items:
        lines.append("(no new regressions)")
        return "\n".join(lines)

    for item in triage_items:
        lines.append(
            f"- {item['file_name']} | line={item['line']} | "
            f"severity={item['severity']} | id={item['finding_id']}"
        )
        lines.append(f"  Message: {item['message']}")
        lines.append(f"  Suggested owner: {item['suggested_owner'] or '-'}")

        if item["existing_task_id"]:
            lines.append(
                f"  Existing task: {item['existing_task_id']} "
                f"(status={item['existing_task_status']})"
            )
        else:
            lines.append("  Existing task: -")

    return "\n".join(lines)


def create_triage_tasks(regression_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    created: List[Dict[str, Any]] = []

    for item in build_triage_items(regression_payload):
        if item["existing_task_id"]:
            continue

        finding = {
            "id": item["finding_id"],
            "file_name": item["file_name"],
            "line": item["line"],
            "severity": item["severity"],
            "message": item["message"],
        }

        owner = item["suggested_owner"]
        task_id = _make_task_id(item["finding_id"])
        title = _make_task_title(finding)
        notes = (
            f"[{finding['severity'].upper()}] {finding['message']} "
            f"(file={finding['file_name']}, line={finding['line']}, finding_id={finding['id']})"
        )

        work_item = create_work_item(
            task_id=task_id,
            title=title,
            primary_owner=owner,
            assignees=[owner] if owner else [],
            files=[finding["file_name"]],
            finding_ids=[finding["id"]],
            notes=notes,
            blockers=[],
            collaborators=[],
            watchers=[],
        )

        created.append(work_item.to_dict())

    return created


def sync_triage_tasks(regression_payload: Dict[str, Any]) -> Dict[str, Any]:
    new_ids = {item.get("id", "") for item in regression_payload.get("new_findings", [])}
    existing_ids = {item.get("id", "") for item in regression_payload.get("existing_findings", [])}
    active_ids = new_ids | existing_ids

    updated_to_done: List[str] = []
    kept_open: List[str] = []

    for work_item in get_all_work_items():
        if not work_item.finding_ids:
            continue

        matched_ids = set(work_item.finding_ids)

        if matched_ids & active_ids:
            if work_item.status == "done":
                update_work_item(
                    work_item.id,
                    status="review",
                )
                kept_open.append(work_item.id)
            else:
                kept_open.append(work_item.id)
            continue

        resolved_match = any(
            finding.get("id", "") in matched_ids
            for finding in regression_payload.get("resolved_findings", [])
        )

        if resolved_match and work_item.status != "done":
            update_work_item(
                work_item.id,
                status="done",
            )
            updated_to_done.append(work_item.id)

    created = create_triage_tasks(regression_payload)

    return {
        "created_task_count": len(created),
        "created_tasks": created,
        "marked_done_count": len(updated_to_done),
        "marked_done_task_ids": updated_to_done,
        "kept_open_count": len(kept_open),
        "kept_open_task_ids": kept_open,
    }
