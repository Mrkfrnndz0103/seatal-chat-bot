from __future__ import annotations

import logging
from typing import Any

from app.seatalk.client import SeaTalkClient
from app.workflows.helpers import (
    build_sheet_update_text,
    send_text_from_workflow,
    supports_by_keyword,
)

logger = logging.getLogger("seatalk_bot")


class BacklogsWorkflow:
    name = "backlogs"

    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.seatalk_client = seatalk_client

    def supports(self, payload: dict[str, Any]) -> bool:
        return supports_by_keyword(payload, self.name)

    def process(self, payload: dict[str, Any]) -> None:
        event = payload.get("event", {}) if isinstance(payload.get("event", {}), dict) else {}
        drive_file_id = str(event.get("drive_file_id", "") or event.get("file_id", "") or "").strip()

        message = build_sheet_update_text(self.name, payload)

        # Optional: trigger the backlog Drive->Sheet pipeline when a file id is provided.
        if drive_file_id:
            try:
                from app.workflows.backlogs.backlogs_update import process_backlogs_update

                result = process_backlogs_update(drive_file_id)
                status = str(result.get("status", "ok"))
                rows = result.get("rows_written")
                if rows is not None:
                    message = f"{message}\nstatus: {status}\nrows_written: {rows}"
                else:
                    message = f"{message}\nstatus: {status}"
            except Exception as exc:
                logger.exception("Backlogs pipeline failed for file_id=%s", drive_file_id)
                message = f"{message}\nstatus: failed\nerror: {exc}"

        send_text_from_workflow(self.seatalk_client, payload, message)
