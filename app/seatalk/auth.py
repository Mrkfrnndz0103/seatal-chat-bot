import threading
import time
from typing import Any

import requests

from app.config import settings


class SeaTalkAuthManager:
    def __init__(self) -> None:
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            now = time.time()
            # Refresh early to avoid edge-expiry failures.
            if self._access_token and now < self._expires_at - 30:
                return self._access_token

            payload = {
                "app_id": settings.seatalk_app_id,
                "app_secret": settings.seatalk_app_secret,
            }
            response = requests.post(settings.seatalk_auth_url, json=payload, timeout=15)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            token = (
                data.get("app_access_token")
                or data.get("access_token")
                or data.get("token")
                or data.get("data", {}).get("access_token")
            )
            expire_at = data.get("expire")
            if expire_at:
                expires_in = max(int(expire_at) - int(now), 60)
            else:
                expires_in = (
                    data.get("expires_in")
                    or data.get("expire_in")
                    or data.get("data", {}).get("expires_in")
                    or 3600
                )

            if not token:
                raise RuntimeError(f"SeaTalk auth response missing token: {data}")

            self._access_token = str(token)
            self._expires_at = now + int(expires_in)
            return self._access_token
