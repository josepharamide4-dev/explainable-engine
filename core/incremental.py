import hashlib
import json
from pathlib import Path

from core.scanner import scan_python_file


def file_hash(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def build_scan_state(project_path: str) -> dict:
    base = Path(project_path)

    files = []

    for path in sorted(base.rglob("*.py")):
        relative = path.relative_to(base).as_posix()

        files.append(
            {
                "path": relative,
                "hash": file_hash(path),
            }
        )

    return {
        "version": 1,
        "project_path": str(base),
        "file_count": len(files),
        "files": files,
    }


def compare_states(old_state: dict, new_state: dict) -> dict:
    old_map = {f["path"]: f["hash"] for f in old_state.get("files", [])}
    new_map = {f["path"]: f["hash"] for f in new_state.get("files", [])}

    changed = []
    added = []
    removed = []

    for path, new_hash in new_map.items():
        if path not in old_map:
            added.append(path)
        elif old_map[path] != new_hash:
            changed.append(path)

    for path in old_map:
        if path not in new_map:
            removed.append(path)

    return {
        "changed": sorted(changed),
        "added": sorted(added),
        "removed": sorted(removed),
    }


def save_state(payload: dict, state_path: str):
    Path(state_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state(state_path: str) -> dict:
    path = Path(state_path)

    if not path.exists():
        raise FileNotFoundError(state_path)

    return json.loads(path.read_text(encoding="utf-8"))


def incremental_scan(project_path: str, state_path: str):
    base = Path(project_path)

    previous_state_found = Path(state_path).exists()

    new_state = build_scan_state(project_path)

    if not previous_state_found:
        changed_files = [f["path"] for f in new_state["files"]]
        removed_files = []
    else:
        old_state = load_state(state_path)
        diff = compare_states(old_state, new_state)

        changed_files = diff["changed"] + diff["added"]
        removed_files = diff["removed"]

    reports = []

    for relative in changed_files:
        file_path = base / relative

        if file_path.exists():
            report = scan_python_file(str(file_path))
            reports.append(report)

    return {
        "previous_state_found": previous_state_found,
        "changed_files": sorted(changed_files),
        "removed_files": sorted(removed_files),
        "reports": reports,
        "new_state": new_state,
    }


def render_incremental(payload: dict) -> str:
    lines = []

    if not payload["previous_state_found"]:
        lines.append("First run — scanning all Python files.")
    else:
        lines.append("Incremental scan:")

    lines.append("")

    if payload["changed_files"]:
        lines.append("Changed files:")
        for f in payload["changed_files"]:
            lines.append(f"- {f}")
    else:
        lines.append("No changed files.")

    if payload["removed_files"]:
        lines.append("")
        lines.append("Removed files:")
        for f in payload["removed_files"]:
            lines.append(f"- {f}")

    lines.append("")
    lines.append(f"Reports generated: {len(payload['reports'])}")

    return "\n".join(lines)