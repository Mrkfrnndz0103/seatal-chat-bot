from __future__ import annotations

import logging
from typing import Any

from app.seatalk.client import SeaTalkClient
from app.workflows.automation.workflow import AutomationWorkflow
from app.workflows.backlogs.workflow import BacklogsWorkflow
from app.workflows.lhpending_request.workflow import LHPendingRequestWorkflow
from app.workflows.mdt.workflow import MDTWorkflow
from app.workflows.stuckup.workflow import StuckupWorkflow
from app.workflows.types import WorkflowPipeline

logger = logging.getLogger("seatalk_bot")


class AutomationWorkflowManager:
    def __init__(self, seatalk_client: SeaTalkClient) -> None:
        self.base_automation = AutomationWorkflow(seatalk_client)
        self.workflows: list[WorkflowPipeline] = [
            BacklogsWorkflow(seatalk_client),
            StuckupWorkflow(seatalk_client),
            LHPendingRequestWorkflow(seatalk_client),
            MDTWorkflow(seatalk_client),
        ]

    def process(self, payload: dict[str, Any]) -> None:
        # Keep existing platform-automation behavior (typing, welcome, click response).
        self.base_automation.process(payload)

        for workflow in self.workflows:
            try:
                if workflow.supports(payload):
                    workflow.process(payload)
            except Exception:
                logger.exception("workflow '%s' failed", workflow.name)
