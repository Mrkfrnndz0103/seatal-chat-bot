from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.seatalk.client import SeaTalkClient


@dataclass
class WorkflowContext:
    event_type: str
    group_id: str
    employee_code: str
    thread_id: str
    text: str
    callback_value: str
    sheet_text: str
    sheet_img_1: str


def extract_context(payload: dict[str, Any]) -> WorkflowContext:
    event_type = str(payload.get("event_type", "") or "")
    event = payload.get("event", {})
    message = event.get("message", {})
    sender = message.get("sender", {})

    text_obj = message.get("text", {}) if isinstance(message, dict) else {}
    text = ""
    if isinstance(text_obj, dict):
        text = str(text_obj.get("plain_text") or text_obj.get("content") or "").strip()

    callback_value = str(event.get("value", "") or "").strip()
    group_id = str(event.get("group_id", "") or event.get("group", {}).get("group_id", "") or "")
    employee_code = str(event.get("employee_code", "") or sender.get("employee_code", "") or "")
    thread_id = str(event.get("thread_id", "") or message.get("thread_id", "") or "")

    sheet_update = event.get("sheet_update", {}) if isinstance(event.get("sheet_update", {}), dict) else {}
    sheet_text = str(sheet_update.get("text", "") or "").strip()
    sheet_img_1 = str(sheet_update.get("img_1", "") or "").strip()

    return WorkflowContext(
        event_type=event_type,
        group_id=group_id,
        employee_code=employee_code,
        thread_id=thread_id,
        text=text,
        callback_value=callback_value,
        sheet_text=sheet_text,
        sheet_img_1=sheet_img_1,
    )


def supports_by_keyword(payload: dict[str, Any], workflow_name: str) -> bool:
    ctx = extract_context(payload)
    event = payload.get("event", {})

    if ctx.event_type == "workflow_update" and str(event.get("workflow", "") or "").strip() == workflow_name:
        return True

    keyword = workflow_name.lower()
    trigger_tokens = {
        keyword,
        f"/{keyword}",
        f"workflow:{keyword}",
    }

    text_lower = ctx.text.lower()
    callback_lower = ctx.callback_value.lower()

    return any(token in text_lower for token in trigger_tokens) or any(
        token in callback_lower for token in trigger_tokens
    )


def build_sheet_update_text(workflow_name: str, payload: dict[str, Any]) -> str:
    ctx = extract_context(payload)
    lines = [f"[{workflow_name}] workflow update"]

    if ctx.sheet_text:
        lines.append(ctx.sheet_text)
    elif ctx.text:
        lines.append(ctx.text)
    else:
        lines.append("No sheet text provided.")

    if ctx.sheet_img_1:
        # SeaTalk image API needs base64 payload; include URL/reference in text for now.
        lines.append(f"img_1: {ctx.sheet_img_1}")

    return "\n".join(lines)


def send_text_from_workflow(
    seatalk_client: SeaTalkClient,
    payload: dict[str, Any],
    text: str,
) -> None:
    ctx = extract_context(payload)
    if ctx.group_id:
        seatalk_client.send_group_text(
            group_id=ctx.group_id,
            content=text,
            thread_id=ctx.thread_id,
        )
        return

    if ctx.employee_code:
        seatalk_client.send_single_text(
            employee_code=ctx.employee_code,
            content=text,
            thread_id=ctx.thread_id,
        )
