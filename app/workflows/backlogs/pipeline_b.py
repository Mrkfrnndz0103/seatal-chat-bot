import base64
import os
import logging
from workflows.backlogs.group_store import list_group_ids
from utils import send_group_chat_message
import httpx
from dotenv import load_dotenv

logger = logging.getLogger("backlogs_pipeline_b")

load_dotenv()

def _get_env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


async def _export_dashboard_pdf() -> bytes:
    sheet_id = _get_env("BACKLOGS_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("BACKLOGS_SHEET_ID must be set")

    gid = _get_env("BACKLOGS_DASHBOARD_GID", "2030780141")
    rng = _get_env("BACKLOGS_DASHBOARD_RANGE", "B2:R59")

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
    params = {
        "format": "pdf",
        "gid": gid,
        "range": rng,
        "scale": _get_env("BACKLOGS_DASHBOARD_SCALE", "2"),
        "sheetnames": "false",
        "printtitle": "false",
        "gridlines": "false",
    }

    # Use service account auth if provided
    token = None
    sa_path = _get_env("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_path:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GoogleRequest

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
        creds.refresh(GoogleRequest())
        token = creds.token

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.content


async def _pdf_to_png_base64(pdf_bytes: bytes) -> str:
    renderer_url = _get_env("BACKLOGS_PDF_RENDERER_URL")
    if not renderer_url:
        raise RuntimeError("BACKLOGS_PDF_RENDERER_URL must be set for PDF->PNG conversion")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            renderer_url,
            headers={"Content-Type": "application/pdf"},
            content=pdf_bytes,
        )
        resp.raise_for_status()
        data = resp.json()
        if "png_base64" not in data:
            raise RuntimeError("Renderer did not return png_base64")
        return data["png_base64"]


async def notify_backlogs_dashboard():
    group_ids = list_group_ids()
    if not group_ids:
        logger.warning("No SeaTalk group IDs registered; skipping notify.")
        return {"status": "skipped", "reason": "no_groups"}

    text = _get_env("BACKLOGS_SEATALK_TEXT", "OB Pending for Dispatch update")
    pdf_bytes = await _export_dashboard_pdf()
    img_b64 = await _pdf_to_png_base64(pdf_bytes)

    results = []
    for gid in group_ids:
        # Send text
        res_text = await send_group_chat_message(group_id=gid, content=text)
        # Send image
        res_img = await _send_group_image(gid, img_b64)
        results.append({"group_id": gid, "text": res_text, "image": res_img})
    return {"status": "ok", "results": results}


async def _send_group_image(group_id: str, img_b64: str):
    token = await _get_seatalk_token()
    if not token:
        return {"status": "error_no_token"}

    webhook_id = _get_env("SEATALK_WEBHOOK_GROUP")
    if not webhook_id:
        return {"status": "failed_no_webhook"}

    # Use group webhook for image
    url = "https://openapi.seatalk.io/webhook/group/" + webhook_id

    payload = {
        "tag": "image",
        "image_base64": {"content": img_b64},
    }
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except Exception:
            logger.error("SeaTalk image send failed: %s %s", resp.status_code, resp.text)
            return {"status": "failed"}
        return {"status": "sent"}


async def _get_seatalk_token():
    from utils import get_seatalk_token
    return await get_seatalk_token()
