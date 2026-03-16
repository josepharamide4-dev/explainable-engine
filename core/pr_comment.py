from typing import Dict, List


def _render_team_context_block(team_context: Dict) -> List[str]:
    lines: List[str] = []

    people = team_context.get("people", {})
    tasks = team_context.get("tasks", [])
    notes = team_context.get("notes", [])

    owners = people.get("owners", [])
    watchers = people.get("watchers", [])
    influencing = people.get("influencing_members", [])

    if owners:
        lines.append(f"  - Owners: {', '.join(owners)}")
    if watchers:
        lines.append(f"  - Watchers: {', '.join(watchers)}")
    if influencing:
        lines.append(f"  - Influencing members: {', '.join(influencing)}")

    if tasks:
        lines.append("  - Active work items:")
        for task in tasks[:3]:
            lines.append(
                f"    - {task['id']} | {task['title']} | "
                f"status={task['status']} | owner={task['primary_owner'] or '-'}"
            )

    if notes:
        lines.append("  - Related notes:")
        for note in notes[:3]:
            lines.append(
                f"    - {note['id']} | {note['body']}"
            )

    return lines


def render_pr_comment(payload: Dict) -> str:
    regression = payload.get("regression")
    if not regression:
        return (
            "## Explainable Report\n\n"
            "No regression payload was provided."
        )

    new_findings = regression.get("new_findings", [])
    resolved_findings = regression.get("resolved_findings", [])

    lines: List[str] = [
        "## Explainable Regression Report",
        "",
        f"- New findings: **{regression.get('new_finding_count', 0)}**",
        f"- Resolved findings: **{regression.get('resolved_finding_count', 0)}**",
        f"- Existing findings: **{regression.get('existing_finding_count', 0)}**",
        f"- Regression detected: **{regression.get('regression_detected', False)}**",
        "",
    ]

    if new_findings:
        lines.append("### New regressions")
        lines.append("")
        for item in new_findings[:10]:
            lines.append(
                f"- `{item['file_name']}:{item['line']}` "
                f"**{item['severity']}** — {item['message']}"
            )
            lines.extend(_render_team_context_block(item.get("team_context", {})))
            lines.append("")
    else:
        lines.append("### New regressions")
        lines.append("")
        lines.append("None.")
        lines.append("")

    if resolved_findings:
        lines.append("### Resolved findings")
        lines.append("")
        for item in resolved_findings[:10]:
            lines.append(
                f"- `{item['file_name']}:{item['line']}` "
                f"**{item['severity']}** — {item['message']}"
            )
        lines.append("")
    else:
        lines.append("### Resolved findings")
        lines.append("")
        lines.append("None.")
        lines.append("")

    return "\n".join(lines)
