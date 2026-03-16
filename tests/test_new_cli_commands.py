import subprocess
import sys


def test_call_graph_command():
    result = subprocess.run(
        [sys.executable, "main.py", "call-graph", "sample_target.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "checkout -> get_discount" in result.stdout
    assert "get_discount -> calculate_discount" in result.stdout


def test_bug_chain_command():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "bug-chain",
            "sample_target.py",
            "--function",
            "calculate_discount",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "checkout -> get_discount -> calculate_discount" in result.stdout