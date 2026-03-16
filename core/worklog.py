import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


WORKLOG_VERSION = 2
DEFAULT_WORKLOG_PATH = ".explainable-worklog.json"

VALID_STATUSES = {
    "todo",
    "in_progress",
    "blocked",
    "review",
    "done",
}

VALID_NOTE_VISIBILITY = {
    "project",
    "restricted",
}

MENTION_PATTERN = re.compile(r"@([A-Za-z0-9._ -]+)")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_person_name(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_file_path(value: str) -> str:
    return value.strip().replace("\\", "/")


def extract_mentions(text: str) -> List[str]:
    matches = MENTION_PATTERN.findall(text or "")
    normalized = [normalize_person_name(match) for match in matches]
    return _normalize_unique_people(normalized)


@dataclass
class AssignmentEvent:
    action: str
    person: str
    timestamp: str
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "person": self.person,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


@dataclass
class ProjectMember:
    name: str
    role: str = ""
    active: bool = True
    influence_files: List[str] = field(default_factory=list)
    influence_finding_ids: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "influence_files": list(self.influence_files),
            "influence_finding_ids": list(self.influence_finding_ids),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMember":
        return cls(
            name=data["name"],
            role=data.get("role", ""),
            active=bool(data.get("active", True)),
            influence_files=list(data.get("influence_files", [])),
            influence_finding_ids=list(data.get("influence_finding_ids", [])),
            notes=data.get("notes", ""),
        )


@dataclass
class CodeNote:
    id: str
    author: str
    body: str
    created_at: str
    updated_at: str
    visibility: str = "project"
    target_files: List[str] = field(default_factory=list)
    target_lines: List[Dict[str, int]] = field(default_factory=list)
    target_finding_ids: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    shared_with: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    handover_note: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "author": self.author,
            "body": self.body,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "visibility": self.visibility,
            "target_files": list(self.target_files),
            "target_lines": list(self.target_lines),
            "target_finding_ids": list(self.target_finding_ids),
            "task_ids": list(self.task_ids),
            "mentions": list(self.mentions),
            "shared_with": list(self.shared_with),
            "tags": list(self.tags),
            "handover_note": self.handover_note,
            "resolved": self.resolved,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeNote":
        return cls(
            id=data["id"],
            author=data["author"],
            body=data["body"],
            created_at=data["created_at"],
            updated_at=data.get("updated_at", data["created_at"]),
            visibility=data.get("visibility", "project"),
            target_files=list(data.get("target_files", [])),
            target_lines=list(data.get("target_lines", [])),
            target_finding_ids=list(data.get("target_finding_ids", [])),
            task_ids=list(data.get("task_ids", [])),
            mentions=list(data.get("mentions", [])),
            shared_with=list(data.get("shared_with", [])),
            tags=list(data.get("tags", [])),
            handover_note=bool(data.get("handover_note", False)),
            resolved=bool(data.get("resolved", False)),
        )


@dataclass
class WorkItem:
    id: str
    title: str
    status: str = "todo"
    primary_owner: str = ""
    assignees: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    finding_ids: List[str] = field(default_factory=list)
    notes: str = ""
    blockers: List[str] = field(default_factory=list)
    collaborators: List[str] = field(default_factory=list)
    watchers: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str = ""
    updated_at: str = field(default_factory=utc_now_iso)
    completed_at: str = ""
    assignment_history: List[AssignmentEvent] = field(default_factory=list)
    linked_note_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "primary_owner": self.primary_owner,
            "assignees": list(self.assignees),
            "files": list(self.files),
            "finding_ids": list(self.finding_ids),
            "notes": self.notes,
            "blockers": list(self.blockers),
            "collaborators": list(self.collaborators),
            "watchers": list(self.watchers),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "assignment_history": [event.to_dict() for event in self.assignment_history],
            "linked_note_ids": list(self.linked_note_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        history = [
            AssignmentEvent(
                action=item.get("action", ""),
                person=item.get("person", ""),
                timestamp=item.get("timestamp", ""),
                reason=item.get("reason", ""),
            )
            for item in data.get("assignment_history", [])
        ]

        return cls(
            id=data["id"],
            title=data["title"],
            status=data.get("status", "todo"),
            primary_owner=data.get("primary_owner", ""),
            assignees=list(data.get("assignees", [])),
            files=list(data.get("files", [])),
            finding_ids=list(data.get("finding_ids", [])),
            notes=data.get("notes", ""),
            blockers=list(data.get("blockers", [])),
            collaborators=list(data.get("collaborators", [])),
            watchers=list(data.get("watchers", [])),
            created_at=data.get("created_at", utc_now_iso()),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", utc_now_iso()),
            completed_at=data.get("completed_at", ""),
            assignment_history=history,
            linked_note_ids=list(data.get("linked_note_ids", [])),
        )


def default_worklog_payload() -> Dict[str, Any]:
    return {
        "version": WORKLOG_VERSION,
        "project_members": [],
        "tasks": [],
        "notes": [],
    }


def load_worklog(path: str = DEFAULT_WORKLOG_PATH) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return default_worklog_payload()

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    validate_worklog_payload(payload)
    return payload


def save_worklog(payload: Dict[str, Any], path: str = DEFAULT_WORKLOG_PATH):
    validate_worklog_payload(payload)
    file_path = Path(path)
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_worklog_payload(payload: Dict[str, Any]):
    if not isinstance(payload, dict):
        raise ValueError("Worklog payload must be a dictionary.")

    version = payload.get("version")
    if version != WORKLOG_VERSION:
        raise ValueError(
            f"Unsupported worklog version: {version!r}. Expected {WORKLOG_VERSION}."
        )

    members = payload.get("project_members")
    tasks = payload.get("tasks")
    notes = payload.get("notes")

    if not isinstance(members, list):
        raise ValueError("Worklog payload must contain a 'project_members' list.")
    if not isinstance(tasks, list):
        raise ValueError("Worklog payload must contain a 'tasks' list.")
    if not isinstance(notes, list):
        raise ValueError("Worklog payload must contain a 'notes' list.")

    seen_member_names = set()
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("Each project member must be a dictionary.")
        name = member.get("name", "")
        if not name or not isinstance(name, str):
            raise ValueError("Each project member must have a non-empty string 'name'.")
        if name in seen_member_names:
            raise ValueError(f"Duplicate project member name found: {name}")
        seen_member_names.add(name)

    seen_task_ids = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Each worklog task must be a dictionary.")

        task_id = task.get("id", "")
        if not task_id or not isinstance(task_id, str):
            raise ValueError("Each worklog task must have a non-empty string 'id'.")

        if task_id in seen_task_ids:
            raise ValueError(f"Duplicate work item id found: {task_id}")

        seen_task_ids.add(task_id)

        status = task.get("status", "todo")
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Work item '{task_id}' has invalid status {status!r}. "
                f"Valid statuses: {sorted(VALID_STATUSES)}"
            )

    seen_note_ids = set()
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError("Each code note must be a dictionary.")

        note_id = note.get("id", "")
        if not note_id or not isinstance(note_id, str):
            raise ValueError("Each code note must have a non-empty string 'id'.")

        if note_id in seen_note_ids:
            raise ValueError(f"Duplicate note id found: {note_id}")

        seen_note_ids.add(note_id)

        visibility = note.get("visibility", "project")
        if visibility not in VALID_NOTE_VISIBILITY:
            raise ValueError(
                f"Code note '{note_id}' has invalid visibility {visibility!r}. "
                f"Valid values: {sorted(VALID_NOTE_VISIBILITY)}"
            )


def get_project_members(path: str = DEFAULT_WORKLOG_PATH) -> List[ProjectMember]:
    payload = load_worklog(path)
    return [ProjectMember.from_dict(member) for member in payload["project_members"]]


def save_project_members(members: List[ProjectMember], path: str = DEFAULT_WORKLOG_PATH):
    payload = load_worklog(path)
    payload["project_members"] = [member.to_dict() for member in members]
    save_worklog(payload, path)


def add_or_update_project_member(
    name: str,
    role: str = "",
    active: bool = True,
    influence_files: Optional[List[str]] = None,
    influence_finding_ids: Optional[List[str]] = None,
    notes: str = "",
    path: str = DEFAULT_WORKLOG_PATH,
) -> ProjectMember:
    normalized_name = normalize_person_name(name)
    members = get_project_members(path)

    updated_member = ProjectMember(
        name=normalized_name,
        role=role.strip(),
        active=active,
        influence_files=_normalize_unique_paths(influence_files or []),
        influence_finding_ids=_normalize_unique_strings(influence_finding_ids or []),
        notes=notes.strip(),
    )

    replaced = False
    for index, member in enumerate(members):
        if member.name == normalized_name:
            members[index] = updated_member
            replaced = True
            break

    if not replaced:
        members.append(updated_member)

    save_project_members(members, path)
    return updated_member


def get_all_work_items(path: str = DEFAULT_WORKLOG_PATH) -> List[WorkItem]:
    payload = load_worklog(path)
    return [WorkItem.from_dict(task) for task in payload["tasks"]]


def save_all_work_items(items: List[WorkItem], path: str = DEFAULT_WORKLOG_PATH):
    payload = load_worklog(path)
    payload["tasks"] = [item.to_dict() for item in items]
    save_worklog(payload, path)


def get_work_item(task_id: str, path: str = DEFAULT_WORKLOG_PATH) -> Optional[WorkItem]:
    for item in get_all_work_items(path):
        if item.id == task_id:
            return item
    return None


def upsert_work_item(item: WorkItem, path: str = DEFAULT_WORKLOG_PATH):
    items = get_all_work_items(path)

    replaced = False
    for index, existing in enumerate(items):
        if existing.id == item.id:
            items[index] = item
            replaced = True
            break

    if not replaced:
        items.append(item)

    save_all_work_items(items, path)


def create_work_item(
    task_id: str,
    title: str,
    primary_owner: str = "",
    assignees: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    finding_ids: Optional[List[str]] = None,
    notes: str = "",
    blockers: Optional[List[str]] = None,
    collaborators: Optional[List[str]] = None,
    watchers: Optional[List[str]] = None,
    path: str = DEFAULT_WORKLOG_PATH,
) -> WorkItem:
    if get_work_item(task_id, path) is not None:
        raise ValueError(f"Work item already exists: {task_id}")

    normalized_primary_owner = normalize_person_name(primary_owner) if primary_owner else ""
    normalized_assignees = _normalize_unique_people(assignees or [])
    normalized_files = _normalize_unique_paths(files or [])
    normalized_finding_ids = _normalize_unique_strings(finding_ids or [])
    normalized_blockers = _normalize_unique_strings(blockers or [])
    normalized_collaborators = _normalize_unique_people(collaborators or [])
    normalized_watchers = _normalize_unique_people(watchers or [])

    if normalized_primary_owner and normalized_primary_owner not in normalized_assignees:
        normalized_assignees.insert(0, normalized_primary_owner)

    item = WorkItem(
        id=task_id,
        title=title.strip(),
        status="todo",
        primary_owner=normalized_primary_owner,
        assignees=normalized_assignees,
        files=normalized_files,
        finding_ids=normalized_finding_ids,
        notes=notes.strip(),
        blockers=normalized_blockers,
        collaborators=normalized_collaborators,
        watchers=normalized_watchers,
    )

    if normalized_primary_owner:
        item.assignment_history.append(
            AssignmentEvent(
                action="assigned",
                person=normalized_primary_owner,
                timestamp=utc_now_iso(),
                reason="Initial primary owner",
            )
        )

    upsert_work_item(item, path)
    return item


def assign_people(
    task_id: str,
    people: List[str],
    primary_owner: str = "",
    reason: str = "",
    path: str = DEFAULT_WORKLOG_PATH,
) -> WorkItem:
    item = _require_work_item(task_id, path)
    changed = False

    normalized_people = _normalize_unique_people(people)
    for person in normalized_people:
        if person not in item.assignees:
            item.assignees.append(person)
            item.assignment_history.append(
                AssignmentEvent(
                    action="assigned",
                    person=person,
                    timestamp=utc_now_iso(),
                    reason=reason,
                )
            )
            changed = True

    normalized_primary_owner = normalize_person_name(primary_owner) if primary_owner else ""
    if normalized_primary_owner:
        if normalized_primary_owner not in item.assignees:
            item.assignees.append(normalized_primary_owner)
            item.assignment_history.append(
                AssignmentEvent(
                    action="assigned",
                    person=normalized_primary_owner,
                    timestamp=utc_now_iso(),
                    reason=reason or "Assigned as primary owner",
                )
            )
        if item.primary_owner != normalized_primary_owner:
            previous_owner = item.primary_owner
            item.primary_owner = normalized_primary_owner
            if previous_owner:
                item.assignment_history.append(
                    AssignmentEvent(
                        action="handover",
                        person=normalized_primary_owner,
                        timestamp=utc_now_iso(),
                        reason=reason or f"Primary ownership moved from {previous_owner}",
                    )
                )
            changed = True

    if changed:
        item.updated_at = utc_now_iso()
        upsert_work_item(item, path)

    return item


def handover_work_item(
    task_id: str,
    from_person: str,
    to_person: str,
    reason: str = "",
    path: str = DEFAULT_WORKLOG_PATH,
) -> WorkItem:
    item = _require_work_item(task_id, path)
    normalized_from = normalize_person_name(from_person)
    normalized_to = normalize_person_name(to_person)

    if normalized_to not in item.assignees:
        item.assignees.append(normalized_to)
        item.assignment_history.append(
            AssignmentEvent(
                action="assigned",
                person=normalized_to,
                timestamp=utc_now_iso(),
                reason=reason or f"Added during handover from {normalized_from}",
            )
        )

    if normalized_from in item.assignees:
        item.assignees = [name for name in item.assignees if name != normalized_from]
        item.assignment_history.append(
            AssignmentEvent(
                action="unassigned",
                person=normalized_from,
                timestamp=utc_now_iso(),
                reason=reason or f"Handed over to {normalized_to}",
            )
        )

    item.primary_owner = normalized_to
    item.assignment_history.append(
        AssignmentEvent(
            action="handover",
            person=normalized_to,
            timestamp=utc_now_iso(),
            reason=reason or f"Ownership handed over from {normalized_from}",
        )
    )
    item.updated_at = utc_now_iso()
    upsert_work_item(item, path)
    return item


def update_work_item(
    task_id: str,
    *,
    title: Optional[str] = None,
    status: Optional[str] = None,
    files: Optional[List[str]] = None,
    finding_ids: Optional[List[str]] = None,
    notes: Optional[str] = None,
    blockers: Optional[List[str]] = None,
    collaborators: Optional[List[str]] = None,
    watchers: Optional[List[str]] = None,
    path: str = DEFAULT_WORKLOG_PATH,
) -> WorkItem:
    item = _require_work_item(task_id, path)

    if title is not None:
        item.title = title.strip()

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Valid statuses: {sorted(VALID_STATUSES)}"
            )
        item.status = status
        if status == "in_progress" and not item.started_at:
            item.started_at = utc_now_iso()
        if status == "done":
            item.completed_at = utc_now_iso()

    if files is not None:
        item.files = _normalize_unique_paths(files)

    if finding_ids is not None:
        item.finding_ids = _normalize_unique_strings(finding_ids)

    if notes is not None:
        item.notes = notes.strip()

    if blockers is not None:
        item.blockers = _normalize_unique_strings(blockers)

    if collaborators is not None:
        item.collaborators = _normalize_unique_people(collaborators)

    if watchers is not None:
        item.watchers = _normalize_unique_people(watchers)

    item.updated_at = utc_now_iso()
    upsert_work_item(item, path)
    return item


def get_all_notes(path: str = DEFAULT_WORKLOG_PATH) -> List[CodeNote]:
    payload = load_worklog(path)
    return [CodeNote.from_dict(note) for note in payload["notes"]]


def save_all_notes(notes: List[CodeNote], path: str = DEFAULT_WORKLOG_PATH):
    payload = load_worklog(path)
    payload["notes"] = [note.to_dict() for note in notes]
    save_worklog(payload, path)


def get_note(note_id: str, path: str = DEFAULT_WORKLOG_PATH) -> Optional[CodeNote]:
    for note in get_all_notes(path):
        if note.id == note_id:
            return note
    return None


def add_code_note(
    note_id: str,
    author: str,
    body: str,
    *,
    visibility: str = "project",
    target_files: Optional[List[str]] = None,
    target_lines: Optional[List[Dict[str, int]]] = None,
    target_finding_ids: Optional[List[str]] = None,
    task_ids: Optional[List[str]] = None,
    shared_with: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    handover_note: bool = False,
    path: str = DEFAULT_WORKLOG_PATH,
) -> CodeNote:
    if get_note(note_id, path) is not None:
        raise ValueError(f"Code note already exists: {note_id}")

    if visibility not in VALID_NOTE_VISIBILITY:
        raise ValueError(
            f"Invalid visibility {visibility!r}. Valid values: {sorted(VALID_NOTE_VISIBILITY)}"
        )

    normalized_author = normalize_person_name(author)
    normalized_target_files = _normalize_unique_paths(target_files or [])
    normalized_target_lines = _normalize_target_lines(target_lines or [])
    normalized_target_finding_ids = _normalize_unique_strings(target_finding_ids or [])
    normalized_task_ids = _normalize_unique_strings(task_ids or [])
    normalized_shared_with = _normalize_unique_people(shared_with or [])
    normalized_tags = _normalize_unique_strings(tags or [])
    normalized_mentions = extract_mentions(body)

    note = CodeNote(
        id=note_id,
        author=normalized_author,
        body=body.strip(),
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        visibility=visibility,
        target_files=normalized_target_files,
        target_lines=normalized_target_lines,
        target_finding_ids=normalized_target_finding_ids,
        task_ids=normalized_task_ids,
        mentions=normalized_mentions,
        shared_with=normalized_shared_with,
        tags=normalized_tags,
        handover_note=handover_note,
        resolved=False,
    )

    notes = get_all_notes(path)
    notes.append(note)
    save_all_notes(notes, path)

    if normalized_task_ids:
        items = get_all_work_items(path)
        changed = False
        for item in items:
            if item.id in normalized_task_ids and note.id not in item.linked_note_ids:
                item.linked_note_ids.append(note.id)
                item.updated_at = utc_now_iso()
                changed = True
        if changed:
            save_all_work_items(items, path)

    return note


def update_code_note(
    note_id: str,
    *,
    body: Optional[str] = None,
    visibility: Optional[str] = None,
    target_files: Optional[List[str]] = None,
    target_lines: Optional[List[Dict[str, int]]] = None,
    target_finding_ids: Optional[List[str]] = None,
    task_ids: Optional[List[str]] = None,
    shared_with: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    resolved: Optional[bool] = None,
    path: str = DEFAULT_WORKLOG_PATH,
) -> CodeNote:
    notes = get_all_notes(path)

    for index, note in enumerate(notes):
        if note.id != note_id:
            continue

        if body is not None:
            note.body = body.strip()
            note.mentions = extract_mentions(note.body)

        if visibility is not None:
            if visibility not in VALID_NOTE_VISIBILITY:
                raise ValueError(
                    f"Invalid visibility {visibility!r}. Valid values: {sorted(VALID_NOTE_VISIBILITY)}"
                )
            note.visibility = visibility

        if target_files is not None:
            note.target_files = _normalize_unique_paths(target_files)

        if target_lines is not None:
            note.target_lines = _normalize_target_lines(target_lines)

        if target_finding_ids is not None:
            note.target_finding_ids = _normalize_unique_strings(target_finding_ids)

        if task_ids is not None:
            note.task_ids = _normalize_unique_strings(task_ids)

        if shared_with is not None:
            note.shared_with = _normalize_unique_people(shared_with)

        if tags is not None:
            note.tags = _normalize_unique_strings(tags)

        if resolved is not None:
            note.resolved = bool(resolved)

        note.updated_at = utc_now_iso()
        notes[index] = note
        save_all_notes(notes, path)
        return note

    raise ValueError(f"Code note not found: {note_id}")


def find_notes_for_code(
    *,
    file_path: str = "",
    line_number: int = 0,
    finding_id: str = "",
    viewer: str = "",
    path: str = DEFAULT_WORKLOG_PATH,
) -> List[CodeNote]:
    normalized_file = normalize_file_path(file_path) if file_path else ""
    normalized_viewer = normalize_person_name(viewer) if viewer else ""

    notes = []
    for note in get_all_notes(path):
        if note.resolved:
            continue

        if not _note_visible_to_person(note, normalized_viewer):
            continue

        file_match = not normalized_file or normalized_file in note.target_files
        finding_match = not finding_id or finding_id in note.target_finding_ids
        line_match = True

        if normalized_file and line_number:
            if note.target_lines:
                line_match = any(
                    entry.get("file", "") == normalized_file
                    and entry.get("line", 0) == line_number
                    for entry in note.target_lines
                )

        if file_match and finding_match and line_match:
            notes.append(note)

    return notes


def find_relevant_people_for_code(
    *,
    file_path: str = "",
    finding_id: str = "",
    path: str = DEFAULT_WORKLOG_PATH,
) -> Dict[str, List[str]]:
    normalized_file = normalize_file_path(file_path) if file_path else ""

    influencing_members = []
    watchers = []
    owners = []

    members = get_project_members(path)
    for member in members:
        if normalized_file and normalized_file in member.influence_files:
            influencing_members.append(member.name)
        if finding_id and finding_id in member.influence_finding_ids:
            influencing_members.append(member.name)

    tasks = get_all_work_items(path)
    for task in tasks:
        if normalized_file and normalized_file in task.files:
            owners.extend(task.assignees)
            watchers.extend(task.watchers)
        if finding_id and finding_id in task.finding_ids:
            owners.extend(task.assignees)
            watchers.extend(task.watchers)

    return {
        "influencing_members": _normalize_unique_people(influencing_members),
        "owners": _normalize_unique_people(owners),
        "watchers": _normalize_unique_people(watchers),
    }


def build_work_board_payload(path: str = DEFAULT_WORKLOG_PATH) -> Dict[str, Any]:
    items = get_all_work_items(path)

    grouped = {status: [] for status in VALID_STATUSES}
    for item in items:
        grouped[item.status].append(item.to_dict())

    for status in grouped:
        grouped[status] = sorted(grouped[status], key=lambda task: task["id"])

    return {
        "version": WORKLOG_VERSION,
        "task_count": len(items),
        "statuses": grouped,
    }


def render_work_board_text(payload: Dict[str, Any]) -> str:
    lines = [
        "Explainable Work Board:",
        "",
        f"Task count: {payload['task_count']}",
        "",
    ]

    for status in ["todo", "in_progress", "blocked", "review", "done"]:
        tasks = payload["statuses"].get(status, [])
        lines.append(status.upper())

        if not tasks:
            lines.append("(none)")
            lines.append("")
            continue

        for task in tasks:
            assignees = ", ".join(task.get("assignees", [])) or "-"
            files = ", ".join(task.get("files", [])) or "-"
            finding_ids = ", ".join(task.get("finding_ids", [])) or "-"
            blockers = ", ".join(task.get("blockers", [])) or "-"
            collaborators = ", ".join(task.get("collaborators", [])) or "-"
            watchers = ", ".join(task.get("watchers", [])) or "-"
            note_ids = ", ".join(task.get("linked_note_ids", [])) or "-"

            lines.append(f"- {task['id']} | {task['title']}")
            lines.append(f"  Primary owner: {task.get('primary_owner') or '-'}")
            lines.append(f"  Assignees: {assignees}")
            lines.append(f"  Collaborators: {collaborators}")
            lines.append(f"  Watchers: {watchers}")
            lines.append(f"  Files: {files}")
            lines.append(f"  Finding IDs: {finding_ids}")
            lines.append(f"  Notes linked: {note_ids}")
            lines.append(f"  Updated: {task.get('updated_at') or '-'}")
            lines.append(f"  Blockers: {blockers}")
            if task.get("notes"):
                lines.append(f"  Notes: {task['notes']}")

        lines.append("")

    return "\n".join(lines).rstrip()


def render_code_notes_text(notes: List[CodeNote]) -> str:
    lines = ["Explainable Code Notes:", ""]
    if not notes:
        lines.append("(none)")
        return "\n".join(lines)

    for note in notes:
        lines.append(f"- {note.id}")
        lines.append(f"  Author: {note.author}")
        lines.append(f"  Visibility: {note.visibility}")
        lines.append(f"  Files: {', '.join(note.target_files) or '-'}")
        lines.append(f"  Finding IDs: {', '.join(note.target_finding_ids) or '-'}")
        lines.append(f"  Task IDs: {', '.join(note.task_ids) or '-'}")
        lines.append(f"  Mentions: {', '.join(note.mentions) or '-'}")
        lines.append(f"  Shared with: {', '.join(note.shared_with) or '-'}")
        lines.append(f"  Created: {note.created_at}")
        lines.append(f"  Updated: {note.updated_at}")
        lines.append(f"  Body: {note.body}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _note_visible_to_person(note: CodeNote, person: str) -> bool:
    if note.visibility == "project":
        return True
    if not person:
        return False
    if person == note.author:
        return True
    if person in note.mentions:
        return True
    if person in note.shared_with:
        return True
    return False


def _normalize_unique_people(values: List[str]) -> List[str]:
    normalized = []
    seen = set()

    for value in values:
        cleaned = normalize_person_name(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _normalize_unique_strings(values: List[str]) -> List[str]:
    normalized = []
    seen = set()

    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _normalize_unique_paths(values: List[str]) -> List[str]:
    normalized = []
    seen = set()

    for value in values:
        cleaned = normalize_file_path(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _normalize_target_lines(values: List[Dict[str, int]]) -> List[Dict[str, int]]:
    normalized = []
    seen = set()

    for entry in values:
        file_value = normalize_file_path(entry.get("file", ""))
        line_value = int(entry.get("line", 0))
        if not file_value or line_value < 1:
            continue
        key = (file_value, line_value)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"file": file_value, "line": line_value})

    return normalized


def _require_work_item(task_id: str, path: str) -> WorkItem:
    item = get_work_item(task_id, path)
    if item is None:
        raise ValueError(f"Work item not found: {task_id}")
    return item