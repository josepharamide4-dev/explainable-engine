from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


DEFAULT_SETTINGS = {
    "scan": {
        "timeout": 2,
        "ignore": ["venv", ".venv", "__pycache__", ".git"],
    },
    "report": {
        "format": "text",
        "save_reports": False,
    },
    "analysis": {
        "detect_infinite_loops": True,
        "detect_none_errors": True,
        "detect_index_errors": True,
    },
    "perf": {
        "top": 10,
        "sort_by": "severity",
        "ignore_file": "",
        "include_file": "",
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_settings(config_path: str = "explainable.toml") -> dict:
    path = Path(config_path)

    if not path.exists():
        return DEFAULT_SETTINGS

    with path.open("rb") as f:
        user_settings = tomllib.load(f)

    return deep_merge(DEFAULT_SETTINGS, user_settings)