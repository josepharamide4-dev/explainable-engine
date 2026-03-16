from core.baseline import (
    approve_current_findings,
    build_baseline_payload,
    load_baseline,
    prune_baseline_payload,
    refresh_baseline_payload,
    save_baseline,
)
from core.scanner import scan_python_file


def test_refresh_preserves_created_at_and_updates_source(tmp_path):
    sample_file = tmp_path / "sample_target.py"
    sample_file.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    report = scan_python_file(sample_file)

    original = {
        "version": 1,
        "path": ".",
        "finding_count": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "source_command": "baseline-create",
        "findings": [],
    }

    payload = refresh_baseline_payload(
        path=".",
        current_reports=[report],
        existing_baseline=original,
    )

    assert payload["created_at"] == "2026-01-01T00:00:00+00:00"
    assert payload["source_command"] == "baseline-refresh"
    assert payload["finding_count"] >= 1


def test_approve_updates_existing_baseline(tmp_path):
    sample_file = tmp_path / "sample_target.py"
    sample_file.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    report = scan_python_file(sample_file)

    existing = {
        "version": 1,
        "path": ".",
        "finding_count": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "source_command": "baseline-create",
        "findings": [],
    }

    payload = approve_current_findings(
        path=".",
        current_reports=[report],
        existing_baseline=existing,
    )

    assert payload["source_command"] == "baseline-approve"
    assert payload["created_at"] == "2026-01-01T00:00:00+00:00"
    assert payload["finding_count"] >= 1


def test_prune_removes_resolved_findings(tmp_path):
    sample_file = tmp_path / "sample_target.py"
    sample_file.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        print(item)
""".strip(),
        encoding="utf-8",
    )

    current_report = scan_python_file(sample_file)
    current_payload = build_baseline_payload(".", [current_report])

    existing = {
        "version": 1,
        "path": ".",
        "finding_count": 2,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "source_command": "baseline-create",
        "findings": current_payload["findings"] + [
            {
                "id": "resolved-finding",
                "file_name": "old.py",
                "line": 10,
                "category": "performance",
                "severity": "high",
                "message": "Old resolved issue",
            }
        ],
    }

    pruned = prune_baseline_payload(
        current_reports=[current_report],
        existing_baseline=existing,
    )

    ids = {item["id"] for item in pruned["findings"]}
    assert "resolved-finding" not in ids
    assert pruned["source_command"] == "baseline-prune"


def test_save_and_load_baseline_round_trip(tmp_path):
    path = tmp_path / ".explainable-baseline.json"
    payload = {
        "version": 1,
        "path": ".",
        "finding_count": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "source_command": "baseline-create",
        "findings": [],
    }

    save_baseline(payload, str(path))
    loaded = load_baseline(str(path))

    assert loaded["version"] == 1
    assert loaded["source_command"] == "baseline-create"
    assert loaded["findings"] == []