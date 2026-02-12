from typing import Any

import requests

from app.config import settings
from app.seatalk.auth import SeaTalkAuthManager


class SeaTalkClient:
    def __init__(self, auth_manager: SeaTalkAuthManager) -> None:
        self.auth_manager = auth_manager

    def send_group_message(self, group_id: str, message: dict[str, Any]) -> dict[str, Any]:
        endpoint = (
            f"{settings.seatalk_api_base_url.rstrip('/')}"
            f"{settings.seatalk_group_message_path}"
        )
        payload: dict[str, Any] = {"group_id": group_id, "message": message}
        return self._post(endpoint, payload)

    def send_single_message(self, employee_code: str, message: dict[str, Any]) -> dict[str, Any]:
        endpoint = (
            f"{settings.seatalk_api_base_url.rstrip('/')}"
            f"{settings.seatalk_single_message_path}"
        )
        payload: dict[str, Any] = {"employee_code": employee_code, "message": message}
        return self._post(endpoint, payload)

    def send_group_text(self, group_id: str, content: str, thread_id: str = "") -> dict[str, Any]:
        message: dict[str, Any] = {"tag": "text", "text": {"format": 2, "content": content}}
        if thread_id:
            message["thread_id"] = thread_id
        return self.send_group_message(group_id=group_id, message=message)

    def send_group_image(self, group_id: str, base64_content: str, thread_id: str = "") -> dict[str, Any]:
        message: dict[str, Any] = {"tag": "image", "image": {"content": base64_content}}
        if thread_id:
            message["thread_id"] = thread_id
        return self.send_group_message(group_id=group_id, message=message)

    def send_group_file(
        self, group_id: str, base64_content: str, filename: str, thread_id: str = ""
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "tag": "file",
            "file": {"content": base64_content, "filename": filename},
        }
        if thread_id:
            message["thread_id"] = thread_id
        return self.send_group_message(group_id=group_id, message=message)

    def send_group_interactive(
        self, group_id: str, elements: list[dict[str, Any]], thread_id: str = ""
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "tag": "interactive_message",
            "interactive_message": {"elements": elements},
        }
        if thread_id:
            message["thread_id"] = thread_id
        return self.send_group_message(group_id=group_id, message=message)

    def send_group_markdown(self, group_id: str, content: str, thread_id: str = "") -> dict[str, Any]:
        message: dict[str, Any] = {"tag": "markdown", "markdown": {"content": content}}
        if thread_id:
            message["thread_id"] = thread_id
        return self.send_group_message(group_id=group_id, message=message)

    def send_single_text(
        self, employee_code: str, content: str, thread_id: str = ""
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tag": "text",
            "text": {"format": 2, "content": content},
        }
        if thread_id:
            payload["thread_id"] = thread_id
        return self.send_single_message(employee_code=employee_code, message=payload)

    def send_single_image(
        self, employee_code: str, base64_content: str, thread_id: str = ""
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "image", "image": {"content": base64_content}}
        if thread_id:
            payload["thread_id"] = thread_id
        return self.send_single_message(employee_code=employee_code, message=payload)

    def send_single_file(
        self, employee_code: str, base64_content: str, filename: str, thread_id: str = ""
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tag": "file",
            "file": {"content": base64_content, "filename": filename},
        }
        if thread_id:
            payload["thread_id"] = thread_id
        return self.send_single_message(employee_code=employee_code, message=payload)

    def send_single_interactive(
        self, employee_code: str, elements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tag": "interactive_message",
            "interactive_message": {"elements": elements},
        }
        return self.send_single_message(employee_code=employee_code, message=payload)

    def send_single_markdown(self, employee_code: str, content: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "markdown", "markdown": {"content": content}}
        return self.send_single_message(employee_code=employee_code, message=payload)

    def set_group_typing_status(self, group_id: str, thread_id: str = "") -> dict[str, Any]:
        endpoint = (
            f"{settings.seatalk_api_base_url.rstrip('/')}"
            f"{settings.seatalk_group_typing_path}"
        )
        payload: dict[str, Any] = {"group_id": group_id}
        if thread_id:
            payload["thread_id"] = thread_id
        return self._post(endpoint, payload)

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = self.auth_manager.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {"ok": True}
