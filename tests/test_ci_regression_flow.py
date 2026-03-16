import json
import subprocess
import sys
from pathlib import Path


def test_baseline_compare_command_runs(tmp_path):
    project = tmp_path

    sample = project / "sample_target.py"
    sample.write_text(
        """
def checkout():
    items = [1, 2, 3]
    for item in items:
        for sub in items:
            print(item, sub)
""".strip(),
        encoding="utf-8",
    )

    baseline = project / ".explainable-baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "version": 1,
                "path": ".",
                "finding_count": 0,
                "findings": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "baseline-compare",
            ".",
            "--baseline",
            str(baseline),
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 2, 3)
