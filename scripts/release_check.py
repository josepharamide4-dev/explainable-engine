from pathlib import Path
import importlib


REQUIRED_PATHS = [
    "main.py",
    "core",
    "config",
    "reporting",
    "tests",
]

OPTIONAL_BUT_RECOMMENDED = [
    "pyproject.toml",
    "explainable.toml",
    "logs",
]


def path_status(path_str: str) -> dict:
    path = Path(path_str)
    return {
        "path": path_str,
        "exists": path.exists(),
        "is_dir": path.is_dir() if path.exists() else False,
        "is_file": path.is_file() if path.exists() else False,
    }


def import_status(module_name: str) -> dict:
    try:
        importlib.import_module(module_name)
        return {
            "module": module_name,
            "ok": True,
            "error": "",
        }
    except Exception as exc:
        return {
            "module": module_name,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_release_payload() -> dict:
    required = [path_status(item) for item in REQUIRED_PATHS]
    recommended = [path_status(item) for item in OPTIONAL_BUT_RECOMMENDED]
    imports = [
        import_status("core.cli"),
        import_status("core.incremental"),
    ]

    missing_required = [item["path"] for item in required if not item["exists"]]
    failed_imports = [item["module"] for item in imports if not item["ok"]]

    ok = not missing_required and not failed_imports

    return {
        "ok": ok,
        "required": required,
        "recommended": recommended,
        "imports": imports,
        "missing_required": missing_required,
        "failed_imports": failed_imports,
    }


def render_release_payload(payload: dict) -> str:
    lines = [
        "Explainable Release Check",
        "",
        f"Overall status: {'PASS' if payload['ok'] else 'FAIL'}",
        "",
        "Required paths:",
    ]

    for item in payload["required"]:
        status = "OK" if item["exists"] else "MISSING"
        lines.append(f"- [{status}] {item['path']}")

    lines.extend(["", "Recommended paths:"])
    for item in payload["recommended"]:
        status = "OK" if item["exists"] else "MISSING"
        lines.append(f"- [{status}] {item['path']}")

    lines.extend(["", "Import checks:"])
    for item in payload["imports"]:
        status = "OK" if item["ok"] else "FAIL"
        lines.append(f"- [{status}] {item['module']}")
        if item["error"]:
            lines.append(f"  Error: {item['error']}")

    if payload["missing_required"]:
        lines.extend(["", "Missing required paths:"])
        for item in payload["missing_required"]:
            lines.append(f"- {item}")

    if payload["failed_imports"]:
        lines.extend(["", "Failed imports:"])
        for item in payload["failed_imports"]:
            lines.append(f"- {item}")

    return "\n".join(lines)


def main():
    payload = build_release_payload()
    print(render_release_payload(payload))
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()