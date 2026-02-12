# SeaTalk LangGraph Bot

This repository includes a runnable FastAPI webhook bot integrated with separate LangGraph pipelines for chat and automation, with full SeaTalk API/event coverage based on `docs/seatalk`.

## Implemented Phases

- `Step 2-3`: dependency setup (`requirements.txt`) for FastAPI, Requests, LangGraph/LangChain, OpenAI-compatible LLM.
- `Step 4`: graph state with user, conversation, message history, and reply fields.
- `Step 5`: graph nodes for event filtering and `call_model` generation.
- `Step 6`: graph edges with conditional routing (`check_message -> call_model or END`).
- `Step 7`: SeaTalk auth manager with token fetch + cache.
- `Step 8`: FastAPI callback endpoint at `/seatalk/callback`.
- `Step 9`: callback routes all documented SeaTalk events through two workflows (`chat_workflow` and `automation_workflow`).

## Project Layout

- `app/main.py`: FastAPI app and webhook with fast ACK + async queueing.
- `app/processing/async_webhook.py`: async worker queue for background event processing.
- `app/seatalk/auth.py`: token fetch/caching.
- `app/seatalk/client.py`: SeaTalk API client (group/single messages + typing status).
- `app/seatalk/events.py`: event router that invokes both workflows.
- `app/workflows/chat/`: LangGraph chat pipeline.
- `app/workflows/automation/`: LangGraph automation pipeline.
- `app/config.py`: env-driven settings.

## Quick Start

1. Create and activate your virtualenv.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy env template and set real values:

```powershell
Copy-Item .env.example .env
```

Important async processing vars:
- `WEBHOOK_WORKER_COUNT` (number of background workers)
- `WEBHOOK_QUEUE_MAXSIZE` (max queued callback events)

4. Run server:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Configure SeaTalk callback URL to:

```text
https://seatalk-bot.romark-fernandez.workers.dev/seatalk/callback
```

## Documentation Auto-Update

Run one-time sync:

```powershell
python scripts/sync_docs.py
```

Run continuous auto-update watcher:

```powershell
python scripts/docs_autoupdate.py
```

When `app/seatalk/event_types.py`, `app/seatalk/client.py`, or `app/seatalk/auth.py` changes, the watcher updates:
- `README.md`
- `docs/implementation_setup_phases.md`

## Callback Verification Behavior

Per `docs/callback.md`, verification requests are handled as:

- Input: `event_type == event_verification` with `event.seatalk_challenge`
- Output: `200` JSON `{ "seatalk_challenge": "..." }`
- Non-verification events are enqueued and ACKed immediately with `200` while workers process them asynchronously.

## Implemented SeaTalk Events

- `bot_added_to_group_chat`
- `interactive_message_click`
- `message_from_bot_subscriber`
- `new_mentioned_message_received_from_group_chat`
- `new_message_received_from_thread`
- `user_enter_chatroom_with_bot`

## Implemented SeaTalk APIs

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

## Cloudflare Worker Callback (Recommended for your setup)

- Worker source: `worker/src/index.js`
- Wrangler config: `worker/wrangler.toml`
- Worker public URL:

```text
https://seatalk-bot.romark-fernandez.workers.dev/seatalk/callback
```

The Worker:
- handles SeaTalk `event_verification` challenge directly.
- forwards non-verification events to your backend: `${BOT_SERVER_URL}/seatalk/callback`.

Deploy/update Worker:

```powershell
cd worker
wrangler deploy
```

## Step 11: Cloud Deployment (Cloudflare Workers + Pages)

Your deployment stack is Cloudflare:

- `Workers`: webhook ingress and SeaTalk callback endpoint.
- `Pages`: frontend/admin UI (if applicable).
- backend bot service: receives forwarded events from Worker at `${BOT_SERVER_URL}/seatalk/callback`.

Recommended deployment flow:

1. Deploy/update Worker:

```powershell
cd worker
wrangler deploy
```

2. Set Worker variable:
- `BOT_SERVER_URL` = your reachable backend bot URL.

3. Configure SeaTalk callback to Worker URL:

```text
https://seatalk-bot.romark-fernandez.workers.dev/seatalk/callback
```

4. Deploy Pages for UI separately (does not replace webhook callback endpoint).

## Notes

- `LLM_BASE_URL` lets you use OpenAI-compatible providers (including DashScope-compatible endpoints).
- SeaTalk callback `Signature` header verification is not included because signing algorithm details are not present in the provided docs.
