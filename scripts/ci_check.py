import json
import sys
from pathlib import Path


EXIT_SUCCESS = 0
EXIT_FAILURE = 2


def load_payload(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Check file not found: {path}")

    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Check file is empty: {path}")

    return json.loads(content)


def build_gate_summary(payload: dict) -> dict:
    regression = payload.get("regression", {})
    doctor = payload.get("doctor", {})
    perf_summary = payload.get("perf_summary", {})

    regression_detected = bool(regression.get("regression_detected", False))
    doctor_status = doctor.get("overall_status", "pass")
    perf_threshold_triggered = bool(perf_summary.get("threshold_triggered", False))

    should_fail = regression_detected or doctor_status in {"warn", "fail"}

    return {
        "should_fail": should_fail,
        "regression_detected": regression_detected,
        "doctor_status": doctor_status,
        "perf_threshold_triggered": perf_threshold_triggered,
        "new_finding_count": regression.get("new_finding_count", 0),
        "resolved_finding_count": regression.get("resolved_finding_count", 0),
        "existing_finding_count": regression.get("existing_finding_count", 0),
    }


def render_summary(summary: dict) -> str:
    lines = [
        "Explainable CI Gate:",
        "",
        f"Doctor status: {summary['doctor_status']}",
        f"Regression detected: {summary['regression_detected']}",
        f"Perf threshold triggered: {summary['perf_threshold_triggered']}",
        f"New findings: {summary['new_finding_count']}",
        f"Resolved findings: {summary['resolved_finding_count']}",
        f"Existing findings: {summary['existing_finding_count']}",
        f"Should fail CI: {summary['should_fail']}",
    ]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/ci_check.py <check_json_path>")
        return 1

    path = sys.argv[1]

    try:
        payload = load_payload(path)
        summary = build_gate_summary(payload)
    except Exception as exc:
        print(f"CI gate error: {type(exc).__name__}: {exc}")
        return EXIT_FAILURE

    print(render_summary(summary))
    return EXIT_FAILURE if summary["should_fail"] else EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())