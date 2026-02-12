import json
import os
import threading

_lock = threading.Lock()


def _store_path():
    return os.environ.get("SEATALK_GROUPS_FILE", "workflows/backlogs/groups.json")


def _read_groups():
    path = _store_path()
    if not os.path.exists(path):
        return {"groups": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"groups": []}


def _write_groups(data):
    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_group_id(group_id: str):
    if not group_id:
        return
    with _lock:
        data = _read_groups()
        groups = set(data.get("groups", []))
        groups.add(group_id)
        data["groups"] = sorted(groups)
        _write_groups(data)


def list_group_ids() -> list[str]:
    with _lock:
        data = _read_groups()
        return list(data.get("groups", []))
