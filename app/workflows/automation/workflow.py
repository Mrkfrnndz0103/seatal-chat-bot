from __future__ import annotations

from typing import Any

from app.seatalk.client import SeaTalkClient
from app.workflows.automation.graph import build_automation_graph


class AutomationWorkflow:
    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.seatalk_client = seatalk_client
        self.graph = build_automation_graph()

    def process(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("event_type", "") or "")
        state = {
            "event_type": event_type,
            "payload": payload,
            "seatalk_client": self.seatalk_client,
            "action": "noop",
            "group_id": "",
            "employee_code": "",
            "thread_id": "",
            "response_text": "",
        }
        self.graph.invoke(state)
