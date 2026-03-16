from scripts.ci_check import build_gate_summary


def test_ci_gate_passes_when_no_regression_and_doctor_pass():
    payload = {
        "doctor": {
            "overall_status": "pass",
        },
        "perf_summary": {
            "threshold_triggered": False,
        },
        "regression": {
            "regression_detected": False,
            "new_finding_count": 0,
            "resolved_finding_count": 1,
            "existing_finding_count": 5,
        },
    }

    summary = build_gate_summary(payload)

    assert summary["should_fail"] is False
    assert summary["regression_detected"] is False
    assert summary["doctor_status"] == "pass"


def test_ci_gate_fails_when_regression_detected():
    payload = {
        "doctor": {
            "overall_status": "pass",
        },
        "perf_summary": {
            "threshold_triggered": False,
        },
        "regression": {
            "regression_detected": True,
            "new_finding_count": 2,
            "resolved_finding_count": 0,
            "existing_finding_count": 3,
        },
    }

    summary = build_gate_summary(payload)

    assert summary["should_fail"] is True
    assert summary["new_finding_count"] == 2


def test_ci_gate_fails_when_doctor_warns():
    payload = {
        "doctor": {
            "overall_status": "warn",
        },
        "perf_summary": {
            "threshold_triggered": False,
        },
        "regression": {
            "regression_detected": False,
            "new_finding_count": 0,
            "resolved_finding_count": 0,
            "existing_finding_count": 0,
        },
    }

    summary = build_gate_summary(payload)

    assert summary["should_fail"] is True
    assert summary["doctor_status"] == "warn"