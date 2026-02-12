from __future__ import annotations

from typing import Any

from app.seatalk.client import SeaTalkClient
from app.workflows.helpers import build_sheet_update_text, send_text_from_workflow, supports_by_keyword


class MDTWorkflow:
    name = "mdt"

    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.seatalk_client = seatalk_client

    def supports(self, payload: dict[str, Any]) -> bool:
        return supports_by_keyword(payload, self.name)

    def process(self, payload: dict[str, Any]) -> None:
        message = build_sheet_update_text(self.name, payload)
        send_text_from_workflow(self.seatalk_client, payload, message)
