import json
import subprocess
import sys


def test_list_functions_json_output():
    result = subprocess.run(
        [sys.executable, "main.py", "list-functions", "sample_target.py", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["file"] == "sample_target.py"
    assert "checkout" in data["functions"]


def test_call_graph_json_output():
    result = subprocess.run(
        [sys.executable, "main.py", "call-graph", "sample_target.py", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["file"] == "sample_target.py"
    assert "checkout" in data["call_graph"]
    assert "get_discount" in data["call_graph"]["checkout"]


def test_bug_chain_json_output():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "bug-chain",
            "sample_target.py",
            "--function",
            "calculate_discount",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["file"] == "sample_target.py"
    assert data["target_function"] == "calculate_discount"
    assert ["checkout", "get_discount", "calculate_discount"] in data["chains"]