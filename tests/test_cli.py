import subprocess
import sys


def test_list_functions_command():
    result = subprocess.run(
        [sys.executable, "main.py", "list-functions", "sample_target.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "checkout" in result.stdout
    assert "healthy_function" in result.stdout


def test_analyze_file_command_runs():
    result = subprocess.run(
        [sys.executable, "main.py", "analyze-file", "sample_target.py", "--function", "checkout"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Problem Type:" in result.stdout