import csv
import io
import logging
import os
import zipfile
from datetime import datetime

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger("backlogs_update")

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _load_credentials():
    cred_path = _get_env("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    if not os.path.exists(cred_path):
        raise RuntimeError(
            f"Service account file not found at {cred_path}. "
            "Set GOOGLE_SERVICE_ACCOUNT_FILE to the correct path."
        )
    try:
        return service_account.Credentials.from_service_account_file(
            cred_path, scopes=SCOPES
        )
    except Exception as exc:
        raise RuntimeError(
            "Invalid service account JSON. Ensure the file is a Google "
            "service account key (type=service_account)."
        ) from exc


def _build_drive_service(creds):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _build_sheets_service(creds):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _looks_utf16le(buf: bytes) -> bool:
    if len(buf) >= 2 and buf[0] == 0xFF and buf[1] == 0xFE:
        return True
    probe_len = min(200, len(buf))
    if probe_len == 0:
        return False
    nulls = sum(1 for b in buf[:probe_len] if b == 0x00)
    return nulls > probe_len * 0.2


def _normalize_text(text: str) -> str:
    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")


def _strip_bom(s: str) -> str:
    return s.replace("\ufeff", "", 1) if isinstance(s, str) else s


def _find_key(row: dict, wanted: str):
    w = wanted.replace(" ", "").replace("_", "").lower()
    for k in row.keys():
        nk = _strip_bom(k).replace(" ", "").replace("_", "").lower()
        if nk == w:
            return k
    return None


def _local_datetime(tz_name: str) -> str:
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = None
    now = datetime.now(tz=tz)
    return f"{now.month}/{now.day}/{now.year} {now.hour}:{now.minute:02d}:{now.second:02d}"


def _download_drive_file(drive, file_id: str) -> bytes:
    request = drive.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


def _iter_csv_rows(csv_bytes: bytes):
    encoding = "utf-16le" if _looks_utf16le(csv_bytes) else "utf-8"
    text = _normalize_text(csv_bytes.decode(encoding, errors="replace"))
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        yield row


def _collect_values_from_zip(zip_bytes: bytes, max_rows: int):
    values = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError("ZIP contains no CSV files.")

        for name in sorted(csv_names):
            with zf.open(name) as f:
                csv_bytes = f.read()
            for row in _iter_csv_rows(csv_bytes):
                values.append(row)
                if len(values) >= max_rows:
                    return values
    return values


def _filter_and_map_rows(rows: list[dict]):
    if not rows:
        return []

    first = rows[0]
    k = {
        "toNumber": _find_key(first, "TO Number"),
        "spxTracking": _find_key(first, "SPX Tracking Number"),
        "receiverName": _find_key(first, "Receiver Name"),
        "toQty": _find_key(first, "TO Order Quantity"),
        "operator": _find_key(first, "Operator"),
        "createTime": _find_key(first, "Create Time"),
        "completeTime": _find_key(first, "Complete Time"),
        "remark": _find_key(first, "Remark"),
        "receiveStatus": _find_key(first, "Receive Status"),
        "stagingAreaId": _find_key(first, "Staging Area ID"),
        "receiverType": _find_key(first, "Receiver type"),
        "currentStation": _find_key(first, "Current Station"),
    }

    required = [
        ("TO Number", k["toNumber"]),
        ("SPX Tracking Number", k["spxTracking"]),
        ("Receiver Name", k["receiverName"]),
        ("TO Order Quantity", k["toQty"]),
        ("Operator", k["operator"]),
        ("Create Time", k["createTime"]),
        ("Complete Time", k["completeTime"]),
        ("Receive Status", k["receiveStatus"]),
        ("Staging Area ID", k["stagingAreaId"]),
        ("Receiver type", k["receiverType"]),
        ("Current Station", k["currentStation"]),
    ]
    missing = [name for name, key in required if not key]
    if missing:
        raise RuntimeError("Missing required columns: " + ", ".join(missing))

    def norm(v):
        return str(v or "").strip().lower()

    out = []
    for row in rows:
        rt = norm(row.get(k["receiverType"]))
        cs = norm(row.get(k["currentStation"]))
        if rt == "station" and cs == "soc 5":
            out.append(
                [
                    row.get(k["toNumber"], ""),
                    row.get(k["spxTracking"], ""),
                    row.get(k["receiverName"], ""),
                    row.get(k["toQty"], ""),
                    row.get(k["operator"], ""),
                    row.get(k["createTime"], ""),
                    row.get(k["completeTime"], ""),
                    row.get(k["remark"], "") if k["remark"] else "",
                    row.get(k["receiveStatus"], ""),
                    row.get(k["stagingAreaId"], ""),
                ]
            )
    return out


def _chunk_values(values: list[list], chunk_size: int):
    for offset in range(0, len(values), chunk_size):
        yield values[offset : offset + chunk_size], offset


def process_backlogs_update(file_id: str) -> dict:
    if not file_id:
        raise RuntimeError("file_id is required")

    creds = _load_credentials()
    drive = _build_drive_service(creds)
    sheets = _build_sheets_service(creds)

    folder_id = _get_env("BACKLOGS_DRIVE_FOLDER_ID")
    sheet_id = _get_env("BACKLOGS_SHEET_ID")
    data_sheet = _get_env("BACKLOGS_DATA_SHEET_NAME", "socpacked_generated_data")
    config_sheet = _get_env("BACKLOGS_CONFIG_SHEET_NAME", "config")
    tz = _get_env("NOTIF_TZ", "Asia/Manila")
    max_rows = int(_get_env("MAX_ROW_COUNT", "500000"))
    batch_size = int(_get_env("BATCH_UPDATE_SIZE", "10"))

    if not folder_id or not sheet_id:
        raise RuntimeError("BACKLOGS_DRIVE_FOLDER_ID and BACKLOGS_SHEET_ID must be set")

    # Fetch file metadata
    file_meta = drive.files().get(fileId=file_id, fields="id,name,mimeType,parents").execute()
    if folder_id not in (file_meta.get("parents") or []):
        logger.info("File %s not in target folder; skipping.", file_id)
        return {"status": "skipped", "reason": "not_in_folder"}

    name = file_meta.get("name", "")
    mime = file_meta.get("mimeType", "")
    if not (name.lower().endswith(".zip") or mime in ("application/zip", "application/x-zip-compressed")):
        logger.info("File %s is not a ZIP; skipping.", file_id)
        return {"status": "skipped", "reason": "not_zip"}

    # Check last processed file ID
    last_resp = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{config_sheet}!B1"
    ).execute()
    last_id = (last_resp.get("values") or [[""]])[0][0] if last_resp else ""
    if last_id == file_id:
        logger.info("Duplicate file %s; skipping.", file_id)
        return {"status": "skipped", "reason": "duplicate"}

    start_time = datetime.now()

    # Mark running
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{config_sheet}!F1",
        valueInputOption="RAW",
        body={"majorDimension": "ROWS", "values": [["RUNNING"]]},
    ).execute()

    try:
        zip_bytes = _download_drive_file(drive, file_id)
        rows = _collect_values_from_zip(zip_bytes, max_rows)
        values = _filter_and_map_rows(rows)

        # Clear existing data
        sheets.spreadsheets().values().clear(
            spreadsheetId=sheet_id, range=f"{data_sheet}!A2:J", body={}
        ).execute()

        if values:
            # Chunk + batch update
            if len(values) >= 100000:
                chunk_size = 2000
            elif len(values) >= 50000:
                chunk_size = 3000
            else:
                chunk_size = 5000

            chunk_payloads = []
            for chunk, offset in _chunk_values(values, chunk_size):
                start_row = 2 + offset
                end_row = start_row + len(chunk) - 1
                rng = f"{data_sheet}!A{start_row}:J{end_row}"
                chunk_payloads.append({"range": rng, "values": chunk})

            # group ranges for batchUpdate
            for i in range(0, len(chunk_payloads), batch_size):
                body = {
                    "valueInputOption": "RAW",
                    "data": chunk_payloads[i : i + batch_size],
                }
                sheets.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id, body=body
                ).execute()

        # Only log if rows exist
        if values:
            log_resp = sheets.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=f"{config_sheet}!A3:C"
            ).execute()
            existing = log_resp.get("values", []) if log_resp else []
            check_time = _local_datetime(tz)
            status = "Updated"
            import_complete = _local_datetime(tz)
            new_row = [check_time, status, import_complete]
            combined = [new_row] + existing
            combined = combined[:500]

            sheets.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{config_sheet}!A3:C",
                valueInputOption="RAW",
                body={"majorDimension": "ROWS", "values": combined},
            ).execute()

            # Save duration
            duration_sec = round((datetime.now() - start_time).total_seconds(), 2)
            sheets.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{config_sheet}!D1",
                valueInputOption="RAW",
                body={"majorDimension": "ROWS", "values": [[str(duration_sec)]]},
            ).execute()

        # Save last processed file id
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{config_sheet}!B1",
            valueInputOption="RAW",
            body={"majorDimension": "ROWS", "values": [[file_id]]},
        ).execute()

    except HttpError as err:
        logger.error("Google API error: %s", err)
        raise
    finally:
        # Mark idle
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{config_sheet}!F1",
            valueInputOption="RAW",
            body={"majorDimension": "ROWS", "values": [["IDLE"]]},
        ).execute()

    # Trigger Pipeline B after completion (optional)
    notify_url = _get_env("BACKLOGS_NOTIFY_WEBHOOK_URL")
    if notify_url:
        try:
            import httpx

            httpx.post(notify_url, timeout=10)
        except Exception:
            logger.exception("Failed to trigger backlogs notify webhook")

    return {"status": "ok", "rows_written": len(values)}


def process_backlogs_filtered_rows(rows: list[list], source_file_id: str | None = None) -> dict:
    from app.workflows.backlogs.supabase_client import insert_backlogs_rows
    batch_size = int(_get_env("SUPABASE_INSERT_BATCH_SIZE", "2000"))

    if not rows:
        return {"status": "ok", "rows_written": 0}

    if not source_file_id:
        source_file_id = "unknown"

    payload = []
    for r in rows:
        payload.append(
            {
                "source_file_id": source_file_id,
                "to_number": r[0] if len(r) > 0 else "",
                "spx_tracking_number": r[1] if len(r) > 1 else "",
                "receiver_name": r[2] if len(r) > 2 else "",
                "to_order_quantity": r[3] if len(r) > 3 else "",
                "operator": r[4] if len(r) > 4 else "",
                "create_time": r[5] if len(r) > 5 else "",
                "complete_time": r[6] if len(r) > 6 else "",
                "remark": r[7] if len(r) > 7 else "",
                "receive_status": r[8] if len(r) > 8 else "",
                "staging_area_id": r[9] if len(r) > 9 else "",
            }
        )

    inserted = insert_backlogs_rows(payload, batch_size=batch_size)
    return {"status": "ok", "rows_written": inserted}


def get_latest_drive_file_id() -> str | None:
    creds = _load_credentials()
    drive = _build_drive_service(creds)
    folder_id = _get_env("BACKLOGS_DRIVE_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("BACKLOGS_DRIVE_FOLDER_ID must be set")

    query = f"'{folder_id}' in parents and trashed = false"
    resp = drive.files().list(
        q=query,
        fields="files(id,name,createdTime,mimeType,parents)",
        orderBy="createdTime desc",
        pageSize=1,
    ).execute()
    files = resp.get("files", [])
    if not files:
        return None
    return files[0].get("id") or None
