import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.context_enrichment import build_code_context


BASELINE_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _report_finding_entry(report, finding: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": finding.get("id", ""),
        "file_name": report.file_name,
        "line": finding.get("line", 0),
        "category": finding.get("category", ""),
        "severity": finding.get("severity", ""),
        "message": finding.get("message", ""),
    }


def collect_findings_from_reports(reports) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for report in reports:
        for finding in report.performance_scored_findings:
            findings.append(_report_finding_entry(report, finding))

    findings.sort(
        key=lambda item: (
            item["file_name"],
            item["line"],
            item["severity"],
            item["message"],
            item["id"],
        )
    )
    return findings


def build_baseline_payload(
    path: str,
    reports,
    *,
    existing_baseline: Dict[str, Any] | None = None,
    source_command: str = "baseline-create",
) -> Dict[str, Any]:
    findings = collect_findings_from_reports(reports)
    now = _utc_now()

    created_at = now
    if existing_baseline:
        created_at = existing_baseline.get("created_at", now)

    return {
        "version": BASELINE_VERSION,
        "path": path,
        "finding_count": len(findings),
        "created_at": created_at,
        "updated_at": now,
        "source_command": source_command,
        "findings": findings,
    }


def save_baseline(payload: Dict[str, Any], baseline_path: str):
    Path(baseline_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_baseline(baseline_path: str) -> Dict[str, Any]:
    path = Path(baseline_path)
    if not path.exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    version = payload.get("version")
    if version != BASELINE_VERSION:
        raise ValueError(
            f"Unsupported baseline version: {version!r}. Expected {BASELINE_VERSION}."
        )

    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Baseline payload must contain a 'findings' list.")

    return payload


def compare_findings(
    current_findings: List[Dict[str, Any]],
    baseline_findings: List[Dict[str, Any]],
):
    current_by_id = {item["id"]: item for item in current_findings}
    baseline_by_id = {item["id"]: item for item in baseline_findings}

    new_ids = sorted(set(current_by_id) - set(baseline_by_id))
    resolved_ids = sorted(set(baseline_by_id) - set(current_by_id))
    existing_ids = sorted(set(current_by_id) & set(baseline_by_id))

    return {
        "new_findings": [current_by_id[item_id] for item_id in new_ids],
        "resolved_findings": [baseline_by_id[item_id] for item_id in resolved_ids],
        "existing_findings": [current_by_id[item_id] for item_id in existing_ids],
    }


def enrich_regression_findings(
    findings: List[Dict[str, Any]],
    viewer: str = "",
) -> List[Dict[str, Any]]:
    enriched = []

    for item in findings:
        merged = dict(item)
        merged["team_context"] = build_code_context(
            file_path=item.get("file_name", ""),
            line_number=item.get("line", 0),
            finding_id=item.get("id", ""),
            viewer=viewer,
        )
        enriched.append(merged)

    return enriched


def build_regression_payload(
    *,
    path: str,
    current_reports,
    baseline_payload: Dict[str, Any],
    viewer: str = "",
) -> Dict[str, Any]:
    current_findings = collect_findings_from_reports(current_reports)
    baseline_findings = baseline_payload.get("findings", [])

    comparison = compare_findings(current_findings, baseline_findings)

    new_findings = enrich_regression_findings(
        comparison["new_findings"],
        viewer=viewer,
    )
    resolved_findings = comparison["resolved_findings"]
    existing_findings = comparison["existing_findings"]

    regression_detected = len(new_findings) > 0

    return {
        "path": path,
        "baseline_path": baseline_payload.get("path", ""),
        "current_finding_count": len(current_findings),
        "baseline_finding_count": len(baseline_findings),
        "new_finding_count": len(new_findings),
        "resolved_finding_count": len(resolved_findings),
        "existing_finding_count": len(existing_findings),
        "regression_detected": regression_detected,
        "new_findings": new_findings,
        "resolved_findings": resolved_findings,
        "existing_findings": existing_findings,
    }


def approve_current_findings(
    *,
    path: str,
    current_reports,
    existing_baseline: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return build_baseline_payload(
        path=path,
        reports=current_reports,
        existing_baseline=existing_baseline,
        source_command="baseline-approve",
    )


def refresh_baseline_payload(
    *,
    path: str,
    current_reports,
    existing_baseline: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return build_baseline_payload(
        path=path,
        reports=current_reports,
        existing_baseline=existing_baseline,
        source_command="baseline-refresh",
    )


def prune_baseline_payload(
    *,
    current_reports,
    existing_baseline: Dict[str, Any],
) -> Dict[str, Any]:
    current_findings = collect_findings_from_reports(current_reports)
    current_ids = {item["id"] for item in current_findings}

    kept_findings = [
        item for item in existing_baseline.get("findings", [])
        if item.get("id", "") in current_ids
    ]

    now = _utc_now()

    return {
        "version": BASELINE_VERSION,
        "path": existing_baseline.get("path", "."),
        "finding_count": len(kept_findings),
        "created_at": existing_baseline.get("created_at", now),
        "updated_at": now,
        "source_command": "baseline-prune",
        "findings": kept_findings,
    }


def render_regression_text(payload: Dict[str, Any]) -> str:
    lines = [
        "Regression Summary:",
        "",
        f"Path: {payload['path']}",
        f"Baseline path: {payload['baseline_path']}",
        f"Current findings: {payload['current_finding_count']}",
        f"Baseline findings: {payload['baseline_finding_count']}",
        f"New findings: {payload['new_finding_count']}",
        f"Resolved findings: {payload['resolved_finding_count']}",
        f"Existing findings: {payload['existing_finding_count']}",
        f"Regression detected: {payload['regression_detected']}",
        "",
        "New regressions:",
    ]

    if not payload["new_findings"]:
        lines.append("(none)")
    else:
        for item in payload["new_findings"]:
            lines.append(
                f"- {item['file_name']} | line={item['line']} | "
                f"severity={item['severity']} | id={item['id']}"
            )
            lines.append(f"  Message: {item['message']}")

            context = item.get("team_context", {})
            people = context.get("people", {})
            tasks = context.get("tasks", [])
            notes = context.get("notes", [])

            owners = people.get("owners", [])
            watchers = people.get("watchers", [])
            influencing = people.get("influencing_members", [])

            if owners:
                lines.append(f"  Owners: {', '.join(owners)}")
            if watchers:
                lines.append(f"  Watchers: {', '.join(watchers)}")
            if influencing:
                lines.append(f"  Influencing members: {', '.join(influencing)}")

            if tasks:
                lines.append("  Active work items:")
                for task in tasks:
                    lines.append(
                        f"    - {task['id']} | {task['title']} | "
                        f"status={task['status']} | owner={task['primary_owner'] or '-'}"
                    )

            if notes:
                lines.append("  Related notes:")
                for note in notes:
                    lines.append(
                        f"    - {note['id']} | author={note['author']} | {note['body']}"
                    )

    lines.extend(["", "Resolved findings:"])
    if not payload["resolved_findings"]:
        lines.append("(none)")
    else:
        for item in payload["resolved_findings"]:
            lines.append(
                f"- {item['file_name']} | line={item['line']} | "
                f"severity={item['severity']} | id={item['id']}"
            )

    return "\n".join(lines)