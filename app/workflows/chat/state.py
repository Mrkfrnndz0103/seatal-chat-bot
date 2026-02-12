from typing import Any, TypedDict


class ChatState(TypedDict):
    user_id: str
    employee_code: str
    conversation_id: str
    thread_id: str
    incoming_text: str
    messages: list[dict[str, str]]
    should_reply: bool
    reply_text: str
    raw_event: dict[str, Any]
