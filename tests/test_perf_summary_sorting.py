import json
import subprocess
import sys


def test_perf_summary_json_includes_sort_and_top():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--sort-by", "findings", "--top", "5", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2

    data = json.loads(result.stdout)
    assert data["sort_by"] == "findings"
    assert data["top"] == 5
    assert len(data["top_files"]) <= 5


def test_perf_summary_text_includes_sort_and_top():
    result = subprocess.run(
        [sys.executable, "main.py", "perf-summary", ".", "--sort-by", "file", "--top", "3"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Sort by: file" in result.stdout
    assert "Top limit: 3" in result.stdout