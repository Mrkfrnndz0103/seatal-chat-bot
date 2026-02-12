from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.seatalk.client import SeaTalkClient
from app.seatalk.event_types import MESSAGE_EVENT_TYPES
from app.workflows.chat.graph import build_chat_graph


class ChatWorkflow:
    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.seatalk_client = seatalk_client
        self.graph = build_chat_graph()
        self.conversation_memory: dict[str, list[dict[str, str]]] = defaultdict(list)

    @staticmethod
    def supports(event_type: str) -> bool:
        return event_type in MESSAGE_EVENT_TYPES

    def process(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("event_type", "") or "")
        event = payload.get("event", {})
        message = event.get("message", {})
        sender = message.get("sender", {})

        incoming_text = self._extract_text(message)
        if not incoming_text:
            return

        group_id = str(event.get("group_id", "") or "")
        employee_code = str(event.get("employee_code", "") or sender.get("employee_code", "") or "")
        thread_id = str(message.get("thread_id", "") or "")
        user_id = str(event.get("seatalk_id", "") or sender.get("seatalk_id", "") or "")
        memory_key = group_id or employee_code
        history = self.conversation_memory[memory_key][-10:] if memory_key else []

        state = {
            "user_id": user_id,
            "employee_code": employee_code,
            "conversation_id": group_id,
            "thread_id": thread_id,
            "incoming_text": incoming_text,
            "messages": history,
            "should_reply": False,
            "reply_text": "",
            "raw_event": {"event_type": event_type, "event": event},
        }

        result = self.graph.invoke(state)
        reply_text = str(result.get("reply_text", "")).strip()
        if not result.get("should_reply") or not reply_text:
            return

        if group_id:
            self.seatalk_client.send_group_text(group_id=group_id, content=reply_text, thread_id=thread_id)
        elif employee_code:
            self.seatalk_client.send_single_text(
                employee_code=employee_code,
                content=reply_text,
                thread_id=thread_id,
            )
        else:
            return

        if memory_key:
            self.conversation_memory[memory_key].append({"role": "user", "content": incoming_text})
            self.conversation_memory[memory_key].append({"role": "assistant", "content": reply_text})
            self.conversation_memory[memory_key] = self.conversation_memory[memory_key][-20:]

    @staticmethod
    def _extract_text(message: dict[str, Any]) -> str:
        tag = str(message.get("tag", "") or "")
        text = message.get("text", {})
        if isinstance(text, dict):
            text_content = str(text.get("plain_text") or text.get("content") or "").strip()
            if text_content:
                return text_content

        if tag == "image":
            return "[User sent an image]"
        if tag == "file":
            filename = str(message.get("file", {}).get("filename", "") or "").strip()
            return f"[User sent a file: {filename}]" if filename else "[User sent a file]"
        if tag == "video":
            return "[User sent a video]"
        return ""
