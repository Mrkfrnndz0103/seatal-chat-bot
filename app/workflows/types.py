from __future__ import annotations

from typing import Any, Protocol


class WorkflowPipeline(Protocol):
    name: str

    def supports(self, payload: dict[str, Any]) -> bool:
        ...

    def process(self, payload: dict[str, Any]) -> None:
        ...
