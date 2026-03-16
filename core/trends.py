import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


HISTORY_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_history(history_path: str) -> Dict[str, Any]:
    path = Path(history_path)
    if not path.exists():
        return {
            "version": HISTORY_VERSION,
            "created_at": _utc_now(),
            "snapshots": [],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("version") != HISTORY_VERSION:
        raise ValueError(
            f"Unsupported history version: {payload.get('version')!r}. "
            f"Expected {HISTORY_VERSION}."
        )

    if not isinstance(payload.get("snapshots"), list):
        raise ValueError("History payload must contain a 'snapshots' list.")

    return payload


def save_history(payload: Dict[str, Any], history_path: str):
    Path(history_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_history_snapshot(
    history_payload: Dict[str, Any],
    *,
    regression_payload: Dict[str, Any],
) -> Dict[str, Any]:
    snapshots = list(history_payload.get("snapshots", []))

    snapshot = {
        "timestamp": _utc_now(),
        "path": regression_payload.get("path", ""),
        "baseline_path": regression_payload.get("baseline_path", ""),
        "new_finding_count": regression_payload.get("new_finding_count", 0),
        "resolved_finding_count": regression_payload.get("resolved_finding_count", 0),
        "existing_finding_count": regression_payload.get("existing_finding_count", 0),
        "regression_detected": regression_payload.get("regression_detected", False),
        "new_findings": [
            {
                "id": item.get("id", ""),
                "file_name": item.get("file_name", ""),
                "line": item.get("line", 0),
                "severity": item.get("severity", ""),
                "message": item.get("message", ""),
            }
            for item in regression_payload.get("new_findings", [])
        ],
        "resolved_findings": [
            {
                "id": item.get("id", ""),
                "file_name": item.get("file_name", ""),
                "line": item.get("line", 0),
                "severity": item.get("severity", ""),
                "message": item.get("message", ""),
            }
            for item in regression_payload.get("resolved_findings", [])
        ],
    }

    snapshots.append(snapshot)

    return {
        "version": HISTORY_VERSION,
        "created_at": history_payload.get("created_at", _utc_now()),
        "updated_at": _utc_now(),
        "snapshots": snapshots,
    }


def _safe_average(values: List[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _build_hot_files(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}

    for snapshot in snapshots:
        for item in snapshot.get("new_findings", []):
            file_name = item.get("file_name", "")
            if not file_name:
                continue
            counts[file_name] = counts.get(file_name, 0) + 1

    ranked = sorted(
        counts.items(),
        key=lambda pair: (-pair[1], pair[0].lower()),
    )

    return [
        {"file_name": file_name, "new_regression_count": count}
        for file_name, count in ranked[:10]
    ]


def _build_resolution_durations_hours(snapshots: List[Dict[str, Any]]) -> List[float]:
    first_seen: Dict[str, datetime] = {}
    durations: List[float] = []

    for snapshot in snapshots:
        ts = _parse_iso(snapshot["timestamp"])

        for item in snapshot.get("new_findings", []):
            finding_id = item.get("id", "")
            if finding_id and finding_id not in first_seen:
                first_seen[finding_id] = ts

        for item in snapshot.get("resolved_findings", []):
            finding_id = item.get("id", "")
            if finding_id and finding_id in first_seen:
                delta_hours = (ts - first_seen[finding_id]).total_seconds() / 3600.0
                if delta_hours >= 0:
                    durations.append(delta_hours)

    return durations


def build_trend_report(history_payload: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = history_payload.get("snapshots", [])

    new_counts = [item.get("new_finding_count", 0) for item in snapshots]
    resolved_counts = [item.get("resolved_finding_count", 0) for item in snapshots]
    regression_flags = [1 if item.get("regression_detected", False) else 0 for item in snapshots]

    resolution_hours = _build_resolution_durations_hours(snapshots)

    return {
        "snapshot_count": len(snapshots),
        "created_at": history_payload.get("created_at", ""),
        "updated_at": history_payload.get("updated_at", ""),
        "latest_timestamp": snapshots[-1]["timestamp"] if snapshots else "",
        "average_new_findings": _safe_average(new_counts),
        "average_resolved_findings": _safe_average(resolved_counts),
        "max_new_findings": max(new_counts) if new_counts else 0,
        "regression_snapshot_rate": _safe_average(regression_flags),
        "hot_files": _build_hot_files(snapshots),
        "mean_time_to_resolution_hours": _safe_average(resolution_hours),
        "resolved_regression_count": len(resolution_hours),
    }


def render_trend_report_text(report: Dict[str, Any]) -> str:
    lines = [
        "Explainable Trend Report:",
        "",
        f"Snapshots: {report['snapshot_count']}",
        f"History created at: {report['created_at']}",
        f"History updated at: {report['updated_at']}",
        f"Latest snapshot: {report['latest_timestamp']}",
        f"Average new findings: {report['average_new_findings']:.2f}",
        f"Average resolved findings: {report['average_resolved_findings']:.2f}",
        f"Max new findings in one snapshot: {report['max_new_findings']}",
        f"Regression snapshot rate: {report['regression_snapshot_rate']:.2f}",
        f"Mean time to resolution (hours): {report['mean_time_to_resolution_hours']:.2f}",
        f"Resolved regression count: {report['resolved_regression_count']}",
        "",
        "Hot files:",
    ]

    hot_files = report.get("hot_files", [])
    if not hot_files:
        lines.append("(none)")
    else:
        for item in hot_files:
            lines.append(
                f"- {item['file_name']} | new regressions={item['new_regression_count']}"
            )

    return "\n".join(lines)