from __future__ import annotations

from datetime import datetime, timezone
import re
from pathlib import Path

EVENT_TYPES_FILE = Path("app/seatalk/event_types.py")
CLIENT_FILE = Path("app/seatalk/client.py")
README_FILE = Path("README.md")
IMPLEMENTATION_FILE = Path("docs/implementation_setup_phases.md")

AUTO_BEGIN = "<!-- AUTO_DOCS:BEGIN -->"
AUTO_END = "<!-- AUTO_DOCS:END -->"


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def parse_event_types(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    values = re.findall(r'^EVENT_[A-Z0-9_]+\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    values = [v for v in values if v != "event_verification"]
    return _ordered_unique(values)


def parse_api_shapes(path: Path) -> tuple[list[str], list[str], bool]:
    text = path.read_text(encoding="utf-8")
    method_names = re.findall(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\(", text, flags=re.MULTILINE)

    group_raw = [m.removeprefix("send_group_") for m in method_names if m.startswith("send_group_")]
    single_raw = [m.removeprefix("send_single_") for m in method_names if m.startswith("send_single_")]

    group_raw = [m for m in group_raw if m not in {"message"}]
    single_raw = [m for m in single_raw if m not in {"message"}]

    label_map = {
        "text": "text",
        "image": "image",
        "file": "file",
        "interactive": "interactive message",
        "markdown": "markdown",
    }
    order = ["text", "image", "file", "interactive", "markdown"]

    def normalize(values: list[str]) -> list[str]:
        value_set = set(values)
        normalized: list[str] = []
        for key in order:
            if key in value_set:
                normalized.append(label_map[key])
        return normalized

    has_typing = "set_group_typing_status" in method_names
    return normalize(group_raw), normalize(single_raw), has_typing


def build_events_section(events: list[str]) -> str:
    return "\n".join([f"- `{event}`" for event in events])


def build_apis_section(group_types: list[str], single_types: list[str], has_typing: bool) -> str:
    lines: list[str] = ["- `POST /auth/app_access_token` (token fetch/cache)"]

    if group_types:
        lines.append("- `POST /messaging/v2/group_chat`:")
        lines.extend([f"  - {item}" for item in group_types])

    if single_types:
        lines.append("- `POST /messaging/v2/single_chat`:")
        lines.extend([f"  - {item}" for item in single_types])

    if has_typing:
        lines.append("- `POST /messaging/v2/group_chat_typing`")

    return "\n".join(lines)


def replace_heading_section(text: str, heading: str, body: str) -> str:
    pattern = rf"(## {re.escape(heading)}\n\n)([\s\S]*?)(?=\n## )"

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{body.rstrip()}\n"

    new_text, count = re.subn(pattern, repl, text, count=1)
    if count != 1:
        raise RuntimeError(f"Unable to locate section: {heading}")
    return new_text


def replace_phase_event_list(text: str, event_lines: str) -> str:
    pattern = r"(5\. Enable all required event subscriptions:\n)([\s\S]*?)(?=\n\n---)"

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{event_lines.rstrip()}"

    new_text, count = re.subn(pattern, repl, text, count=1)
    if count != 1:
        raise RuntimeError("Unable to update Phase 7 event subscription list")
    return new_text


def upsert_auto_block(text: str, block_content: str) -> str:
    marker_block = f"{AUTO_BEGIN}\n{block_content.rstrip()}\n{AUTO_END}"
    pattern = rf"{re.escape(AUTO_BEGIN)}[\s\S]*?{re.escape(AUTO_END)}"

    if re.search(pattern, text):
        return re.sub(pattern, marker_block, text, count=1)

    suffix = "\n\n## Auto-Generated Coverage\n\n" + marker_block + "\n"
    return text.rstrip() + suffix


def sync_files(project_root: Path) -> None:
    events = parse_event_types(project_root / EVENT_TYPES_FILE)
    group_types, single_types, has_typing = parse_api_shapes(project_root / CLIENT_FILE)

    events_section = build_events_section(events)
    apis_section = build_apis_section(group_types, single_types, has_typing)

    readme_path = project_root / README_FILE
    readme_text = readme_path.read_text(encoding="utf-8")
    readme_text = replace_heading_section(readme_text, "Implemented SeaTalk Events", events_section)
    readme_text = replace_heading_section(readme_text, "Implemented SeaTalk APIs", apis_section)
    readme_path.write_text(readme_text, encoding="utf-8")

    implementation_path = project_root / IMPLEMENTATION_FILE
    implementation_text = implementation_path.read_text(encoding="utf-8")
    implementation_text = replace_phase_event_list(implementation_text, events_section)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    auto_block = (
        f"_Generated by `scripts/sync_docs.py` on {now_utc}_\n\n"
        "### Implemented SeaTalk Events\n\n"
        f"{events_section}\n\n"
        "### Implemented SeaTalk APIs\n\n"
        f"{apis_section}"
    )
    implementation_text = upsert_auto_block(implementation_text, auto_block)
    implementation_path.write_text(implementation_text, encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sync_files(root)
    print("Synced docs: README.md and docs/implementation_setup_phases.md")
