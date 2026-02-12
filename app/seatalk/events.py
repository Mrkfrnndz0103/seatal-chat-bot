from __future__ import annotations

import logging
from typing import Any

from app.seatalk.client import SeaTalkClient
from app.workflows.chat.workflow import ChatWorkflow
from app.workflows.manager import AutomationWorkflowManager

logger = logging.getLogger("seatalk_bot")


class SeaTalkEventRouter:
    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.automation_workflow_manager = AutomationWorkflowManager(seatalk_client)
        self.chat_workflow = ChatWorkflow(seatalk_client)

    def handle_event(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("event_type", "") or "")

        # Automation workflow handles operational triggers and side effects.
        try:
            self.automation_workflow_manager.process(payload)
        except Exception:
            logger.exception("automation workflow manager failed for event_type=%s", event_type)

        # Chat workflow handles AI conversational response events.
        if self.chat_workflow.supports(event_type):
            try:
                self.chat_workflow.process(payload)
            except Exception:
                logger.exception("chat_workflow failed for event_type=%s", event_type)
        else:
            logger.info("No chat workflow for event_type=%s", event_type)
