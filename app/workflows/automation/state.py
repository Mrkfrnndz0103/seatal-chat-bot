from typing import Any, TypedDict


class AutomationState(TypedDict):
    event_type: str
    payload: dict[str, Any]
    seatalk_client: Any
    action: str
    group_id: str
    employee_code: str
    thread_id: str
    response_text: str
