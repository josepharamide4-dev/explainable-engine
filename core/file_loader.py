import importlib.util
import inspect
from pathlib import Path


def load_module_from_file(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix != ".py":
        raise ValueError(f"Only Python files are supported: {file_path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_function_from_module(module, function_name: str):
    if not hasattr(module, function_name):
        raise AttributeError(f"Function `{function_name}` was not found in the module.")

    obj = getattr(module, function_name)

    if not inspect.isfunction(obj):
        raise TypeError(f"`{function_name}` exists, but it is not a function.")

    return obj


def get_zero_arg_functions(module):
    functions = {}

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            sig = inspect.signature(obj)

            required_params = [
                p for p in sig.parameters.values()
                if p.default is p.empty
                and p.kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
            ]

            if len(required_params) == 0:
                functions[name] = obj

    return functions