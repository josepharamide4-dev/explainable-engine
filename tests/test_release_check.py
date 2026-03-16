from scripts.release_check import build_release_payload, render_release_payload


def test_build_release_payload_has_expected_keys():
    payload = build_release_payload()

    assert "ok" in payload
    assert "required" in payload
    assert "recommended" in payload
    assert "imports" in payload
    assert "missing_required" in payload
    assert "failed_imports" in payload


def test_release_payload_required_entries_present():
    payload = build_release_payload()
    required_paths = {item["path"] for item in payload["required"]}

    assert "main.py" in required_paths
    assert "core" in required_paths
    assert "config" in required_paths
    assert "reporting" in required_paths
    assert "tests" in required_paths


def test_render_release_payload_outputs_text():
    payload = {
        "ok": True,
        "required": [{"path": "main.py", "exists": True}],
        "recommended": [{"path": "pyproject.toml", "exists": True}],
        "imports": [{"module": "main", "ok": True, "error": ""}],
        "missing_required": [],
        "failed_imports": [],
    }

    text = render_release_payload(payload)

    assert "Explainable Release Check" in text
    assert "Overall status: PASS" in text
    assert "[OK] main.py" in text
    assert "[OK] main" in text