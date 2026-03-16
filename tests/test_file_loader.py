from core.file_loader import load_module_from_file, get_function_from_module, get_zero_arg_functions


def test_load_module_from_file():
    module = load_module_from_file("sample_target.py")
    assert module is not None


def test_get_function_from_module():
    module = load_module_from_file("sample_target.py")
    func = get_function_from_module(module, "checkout")
    assert func.__name__ == "checkout"


def test_get_zero_arg_functions():
    module = load_module_from_file("sample_target.py")
    functions = get_zero_arg_functions(module)

    assert "checkout" in functions
    assert "get_discount" in functions
    assert "healthy_function" in functions
    assert "needs_argument" not in functions