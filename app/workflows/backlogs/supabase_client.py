import os
import logging
import httpx

logger = logging.getLogger("backlogs_supabase")


def _get_env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def get_supabase_config():
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    table = _get_env("SUPABASE_BACKLOGS_TABLE", "backlogs_rows")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return url.rstrip("/"), key, table


def insert_backlogs_rows(rows: list[dict], batch_size: int = 2000) -> int:
    if not rows:
        return 0
    base_url, key, table = get_supabase_config()
    endpoint = f"{base_url}/rest/v1/{table}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    inserted_total = 0
    with httpx.Client(timeout=30) as client:
        for offset in range(0, len(rows), batch_size):
            chunk = rows[offset : offset + batch_size]
            resp = client.post(endpoint, headers=headers, json=chunk)
            try:
                resp.raise_for_status()
            except Exception:
                logger.error("Supabase insert failed: %s %s", resp.status_code, resp.text)
                raise
            data = resp.json()
            inserted_total += len(data) if isinstance(data, list) else 0
    return inserted_total
