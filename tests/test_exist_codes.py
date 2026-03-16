import subprocess
import sys


def test_list_functions_success_exit_code():
    result = subprocess.run(
        [sys.executable, "main.py", "list-functions", "sample_target.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_analyze_file_returns_analysis_exit_code():
    result = subprocess.run(
        [sys.executable, "main.py", "analyze-file", "sample_target.py", "--function", "checkout"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_analyze_file_bad_function_returns_input_error():
    result = subprocess.run(
        [sys.executable, "main.py", "analyze-file", "sample_target.py", "--function", "does_not_exist"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1