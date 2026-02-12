# SeaTalk Workflow Automation Implementation Setup

This guide breaks implementation into phases, each with concrete steps.

## Phase 1: Local Project and Environment Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install project dependencies.

```powershell
pip install -r requirements.txt
```

3. Create runtime config from template.

```powershell
Copy-Item .env.example .env
```

4. Fill required `.env` values.
- `SEATALK_APP_ID`
- `SEATALK_APP_SECRET`
- `LLM_API_KEY`
- Optional tuning: `WEBHOOK_WORKER_COUNT`, `WEBHOOK_QUEUE_MAXSIZE`

---

## Phase 2: Backend Core Services Setup

1. Confirm FastAPI entrypoint is available at `app/main.py`.
2. Confirm SeaTalk auth/token cache is configured in `app/seatalk/auth.py`.
3. Confirm SeaTalk API client methods are available in `app/seatalk/client.py`.
4. Start backend locally.

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Verify local health endpoint.
- `GET http://127.0.0.1:8000/healthz`

---

## Phase 3: LangGraph Workflow Pipelines

1. Configure chat pipeline in `app/workflows/chat/`.
- state definition
- message filtering node
- LLM response node
- graph edges

2. Configure base automation pipeline in `app/workflows/automation/`.
- event routing node
- typing status action
- welcome/action response nodes
- graph edges

3. Configure dedicated automation workflow subfolders:
- `app/workflows/backlogs/`
- `app/workflows/stuckup/`
- `app/workflows/lhpending_request/`
- `app/workflows/mdt/`

4. Confirm workflow dispatcher in `app/workflows/manager.py`.
- runs base automation behavior
- routes payload-triggered workflow updates to each workflow module

5. Confirm unified event router in `app/seatalk/events.py`.
- runs `automation_workflow_manager`
- runs `chat_workflow` for message event types

---

## Phase 4: Webhook ACK + Asynchronous Processing

1. Confirm async queue processor exists in `app/processing/async_webhook.py`.
2. Confirm lifecycle startup/shutdown hooks start background workers.
3. Confirm callback endpoint behavior in `app/main.py`.
- `event_verification`: return `seatalk_challenge` immediately
- other events: enqueue and return immediate `200` ACK

4. Tune queue/worker values in `.env`.
- `WEBHOOK_WORKER_COUNT`
- `WEBHOOK_QUEUE_MAXSIZE`

---

## Phase 5: Cloudflare Worker Ingress Setup

1. Configure Worker files.
- `worker/src/index.js`
- `worker/wrangler.toml`

2. Set Worker variable `BOT_SERVER_URL` to backend bot URL.
- backend endpoint expected: `${BOT_SERVER_URL}/seatalk/callback`

3. Deploy Worker.

```powershell
cd worker
wrangler deploy
```

4. Use this callback URL in SeaTalk Open Platform.

```text
https://seatalk-bot.romark-fernandez.workers.dev/seatalk/callback
```

5. Verify Worker behavior.
- handles verification event directly
- forwards non-verification events to backend

---

## Phase 6: Cloudflare Pages (UI/Admin, Optional)

1. Deploy frontend/admin app to Cloudflare Pages.
2. Keep webhook on Worker (Pages is not the callback endpoint).
3. If UI triggers backend actions, route those API calls to your backend service.

---

## Phase 7: SeaTalk Platform Configuration

1. Open SeaTalk Open Platform app settings.
2. Enable Bot capability and required API permissions.
3. Set callback URL to Worker endpoint.
4. Complete event verification handshake.
5. Enable all required event subscriptions:
- `bot_added_to_group_chat`
- `interactive_message_click`
- `message_from_bot_subscriber`
- `new_mentioned_message_received_from_group_chat`
- `new_message_received_from_thread`
- `user_enter_chatroom_with_bot`

---

## Phase 8: Validation and Go-Live Checklist

1. Verification callback test passes (`seatalk_challenge` returned).
2. Non-verification callback returns fast ACK (`ok`, `queued`).
3. Message events trigger chat workflow replies.
4. Automation events trigger expected actions (typing, welcome, click response).
5. Custom workflow updates trigger target subfolder workflow (`backlogs`, `stuckup`, `lhpending_request`, `mdt`) and send Seatalk message.
6. Worker and backend logs confirm successful forwarding and processing.
7. Production `.env` and Worker vars are set and rotated securely.

---

## Phase 9: Documentation Auto-Update

1. Run one-time docs sync:

```powershell
python scripts/sync_docs.py
```

2. Run watcher for automatic docs refresh during development:

```powershell
python scripts/docs_autoupdate.py
```

3. This keeps these files aligned with current code coverage:
- `README.md`
- `docs/implementation_setup_phases.md`

---

## Troubleshooting Quick Notes

1. If callbacks are received but no reply is sent:
- verify `SEATALK_APP_ID` and `SEATALK_APP_SECRET`
- verify bot has permission/scope for target group or user
- verify outgoing SeaTalk API endpoints and payload formats

2. If callback verification fails:
- confirm exact callback URL path is `/seatalk/callback`
- confirm verification response body is `{ "seatalk_challenge": "..." }`

3. If events are dropped:
- increase `WEBHOOK_QUEUE_MAXSIZE`
- increase `WEBHOOK_WORKER_COUNT`
- check backend performance and LLM latency

## Auto-Generated Coverage

<!-- AUTO_DOCS:BEGIN -->
_Generated by `scripts/sync_docs.py` on 2026-02-12 03:39 UTC_

### Implemented SeaTalk Events

- `bot_added_to_group_chat`
- `interactive_message_click`
- `message_from_bot_subscriber`
- `new_mentioned_message_received_from_group_chat`
- `new_message_received_from_thread`
- `user_enter_chatroom_with_bot`

### Implemented SeaTalk APIs

- `POST /auth/app_access_token` (token fetch/cache)
- `POST /messaging/v2/group_chat`:
  - text
  - image
  - file
  - interactive message
  - markdown
- `POST /messaging/v2/single_chat`:
  - text
  - image
  - file
  - interactive message
  - markdown
- `POST /messaging/v2/group_chat_typing`
<!-- AUTO_DOCS:END -->
