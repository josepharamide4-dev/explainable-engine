from core.trends import (
    append_history_snapshot,
    build_trend_report,
    load_history,
    save_history,
)


def test_load_history_returns_empty_structure_when_missing(tmp_path):
    history = load_history(str(tmp_path / ".missing-history.json"))

    assert history["version"] == 1
    assert history["snapshots"] == []


def test_append_history_snapshot_adds_snapshot():
    history_payload = {
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "snapshots": [],
    }

    regression_payload = {
        "path": ".",
        "baseline_path": ".explainable-baseline.json",
        "new_finding_count": 1,
        "resolved_finding_count": 0,
        "existing_finding_count": 2,
        "regression_detected": True,
        "new_findings": [
            {
                "id": "abc123",
                "file_name": "core/scanner.py",
                "line": 10,
                "severity": "high",
                "message": "Nested loop detected",
            }
        ],
        "resolved_findings": [],
    }

    updated = append_history_snapshot(
        history_payload,
        regression_payload=regression_payload,
    )

    assert len(updated["snapshots"]) == 1
    assert updated["snapshots"][0]["new_finding_count"] == 1
    assert updated["snapshots"][0]["new_findings"][0]["id"] == "abc123"


def test_build_trend_report_computes_hot_files_and_resolution_metrics():
    history_payload = {
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-03T00:00:00+00:00",
        "snapshots": [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "path": ".",
                "baseline_path": ".explainable-baseline.json",
                "new_finding_count": 2,
                "resolved_finding_count": 0,
                "existing_finding_count": 0,
                "regression_detected": True,
                "new_findings": [
                    {
                        "id": "f1",
                        "file_name": "core/scanner.py",
                        "line": 10,
                        "severity": "high",
                        "message": "A",
                    },
                    {
                        "id": "f2",
                        "file_name": "core/runtime_scanner.py",
                        "line": 20,
                        "severity": "medium",
                        "message": "B",
                    },
                ],
                "resolved_findings": [],
            },
            {
                "timestamp": "2026-01-02T00:00:00+00:00",
                "path": ".",
                "baseline_path": ".explainable-baseline.json",
                "new_finding_count": 1,
                "resolved_finding_count": 1,
                "existing_finding_count": 1,
                "regression_detected": True,
                "new_findings": [
                    {
                        "id": "f3",
                        "file_name": "core/scanner.py",
                        "line": 30,
                        "severity": "low",
                        "message": "C",
                    }
                ],
                "resolved_findings": [
                    {
                        "id": "f1",
                        "file_name": "core/scanner.py",
                        "line": 10,
                        "severity": "high",
                        "message": "A",
                    }
                ],
            },
        ],
    }

    report = build_trend_report(history_payload)

    assert report["snapshot_count"] == 2
    assert report["max_new_findings"] == 2
    assert report["hot_files"][0]["file_name"] == "core/scanner.py"
    assert report["resolved_regression_count"] == 1
    assert report["mean_time_to_resolution_hours"] >= 24.0


def test_save_and_load_history_round_trip(tmp_path):
    path = tmp_path / ".explainable-history.json"
    payload = {
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "snapshots": [],
    }

    save_history(payload, str(path))
    loaded = load_history(str(path))

    assert loaded["version"] == 1
    assert loaded["snapshots"] == []