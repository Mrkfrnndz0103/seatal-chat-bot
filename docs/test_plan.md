# SeaTalk Bot Test Plan

This test plan validates the deployed architecture:

- SeaTalk -> Cloudflare Worker -> FastAPI backend
- Fast ACK webhook handling with async queue processing
- `chat_workflow` and `automation_workflow` behavior

## Test Data and Endpoints

Set these variables for command examples:

```powershell
$BACKEND_URL = "https://seatalk-chat-bot.onrender.com"
$WORKER_URL = "https://seatalk-bot.romark-fernandez.workers.dev"
```

## 1. Static Checks

### 1.1 Python compile check

```powershell
python -m compileall app scripts worker
```

Expected:
- Command exits successfully.

### 1.2 Docs sync check

```powershell
python scripts/sync_docs.py
```

Expected:
- Prints `Synced docs: README.md and docs/implementation_setup_phases.md`.

## 2. Backend Smoke Tests

### 2.1 Health endpoint

```powershell
Invoke-RestMethod -Method Get -Uri "$BACKEND_URL/healthz"
```

Expected:
- `status` is `ok`.

### 2.2 Callback verification contract (backend direct)

```powershell
$body = @{
  event_type = "event_verification"
  event = @{ seatalk_challenge = "abc123" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "$WORKER_URL/seatalk/callback" -ContentType "application/json" -Body $body
```

Expected:
- Response JSON includes `seatalk_challenge: "abc123"`.

### 2.3 Fast ACK for non-verification callback

```powershell
$body = @{
  event_id = "test-evt-001"
  event_type = "message_from_bot_subscriber"
  event = @{
    employee_code = "e_test_user"
    seatalk_id = "123456"
    message = @{
      tag = "text"
      text = @{ content = "hello" }
    }
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "$BACKEND_URL/seatalk/callback" -ContentType "application/json" -Body $body
```

Expected:
- Immediate response with `ok = true`.
- Response includes `queued = true` unless queue is full.

## 3. Worker Tests

### 3.1 Worker verification callback

```powershell
$body = @{
  event_type = "event_verification"
  event = @{ seatalk_challenge = "worker-challenge-1" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "$WORKER_URL/seatalk/callback" -ContentType "application/json" -Body $body
```

Expected:
- Worker returns `seatalk_challenge: "worker-challenge-1"`.

### 3.2 Worker forwarding to backend

```powershell
$body = @{
  event_id = "worker-forward-001"
  event_type = "message_from_bot_subscriber"
  event = @{
    employee_code = "e_test_user"
    seatalk_id = "123456"
    message = @{
      tag = "text"
      text = @{ content = "worker forward test" }
    }
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "$WORKER_URL/seatalk/callback" -ContentType "application/json" -Body $body
```

Expected:
- Worker response `ok = true`.
- Backend logs show event processed.

### 3.3 Worker loop protection

Precondition:
- Set `BOT_SERVER_URL` equal to Worker domain and deploy.

Expected:
- Worker response includes:
  - `error = "invalid_bot_server_url"`
  - prevents infinite forwarding loop.

## 4. Workflow Behavior Tests

## 4.1 Chat workflow: 1-1 message event

Send event:

```json
{
  "event_id": "chat-1",
  "event_type": "message_from_bot_subscriber",
  "event": {
    "employee_code": "e_test_user",
    "seatalk_id": "123456",
    "message": {
      "tag": "text",
      "text": { "content": "How can I request leave?" }
    }
  }
}
```

Expected:
- Callback ACKs immediately.
- Background worker triggers `chat_workflow`.
- Bot sends reply via `POST /messaging/v2/single_chat`.

### 4.2 Chat workflow: group mention event

Send event type `new_mentioned_message_received_from_group_chat` with:
- `group_id`
- `message.text.plain_text`
- optional `thread_id`

Expected:
- `chat_workflow` runs.
- Bot replies to group chat (`/messaging/v2/group_chat`), same thread when provided.

### 4.3 Chat workflow: thread-follow event

Send event type `new_message_received_from_thread`.

Expected:
- Bot reply sent as thread reply when `thread_id` exists.

### 4.4 Automation workflow: bot added to group

Send `bot_added_to_group_chat` payload with `event.group.group_id`.

Expected:
- If `BOT_SEND_GROUP_WELCOME=true`, bot posts welcome message to group.

### 4.5 Automation workflow: user enters bot chatroom

Send `user_enter_chatroom_with_bot` with `employee_code`.

Expected:
- If `BOT_SEND_USER_WELCOME=true`, bot sends welcome to user.

### 4.6 Automation workflow: interactive click

Send `interactive_message_click` with `value` plus either `group_id` or `employee_code`.

Expected:
- Bot sends action acknowledgement:
  - `Action received: <value>`

### 4.7 Automation typing status

For message or group interactive events, when `group_id` exists:
- If `BOT_SEND_TYPING_STATUS=true`, app calls `/messaging/v2/group_chat_typing`.

### 4.8 Dedicated workflow folders (`backlogs`, `stuckup`, `lhpending_request`, `mdt`)

Send payload:

```json
{
  "event_type": "workflow_update",
  "event": {
    "workflow": "backlogs",
    "group_id": "12345",
    "sheet_update": {
      "img_1": "https://example.com/chart.png",
      "text": "Backlog moved +12 from yesterday"
    }
  }
}
```

Expected:
- `backlogs` workflow module processes the event.
- Bot sends message to configured group containing workflow label + `text` + `img_1`.

## 5. SeaTalk Platform Integration Tests

### 5.1 Callback handshake

In SeaTalk Open Platform:
- Set callback URL to:
  - `https://seatalk-bot.romark-fernandez.workers.dev/seatalk/callback`

Expected:
- Verification succeeds.

### 5.2 Event subscription tests

Confirm all subscribed events trigger callback delivery:

- `bot_added_to_group_chat`
- `interactive_message_click`
- `message_from_bot_subscriber`
- `new_mentioned_message_received_from_group_chat`
- `new_message_received_from_thread`
- `user_enter_chatroom_with_bot`

Expected:
- Each event appears in Worker/backend logs and is processed by matching workflow.

## 6. Queue and Reliability Tests

### 6.1 Queue saturation behavior

Method:
- Send burst of callbacks quickly.

Expected:
- Callback still returns HTTP 200.
- If queue exceeds capacity, response shows `queued=false` and logs indicate queue full.

### 6.2 Worker count tuning

Change:
- `WEBHOOK_WORKER_COUNT`
- `WEBHOOK_QUEUE_MAXSIZE`

Expected:
- Higher worker count improves throughput for background processing.

## 7. Security and Config Tests

### 7.1 Secret files ignored by git

```powershell
git status --short
```

Expected:
- `.env` and credential files (e.g., `service_account.json`) do not appear as untracked/tracked changes.

### 7.2 Worker var configured correctly

Expected:
- `BOT_SERVER_URL` points to backend service URL, not Worker URL.

## 8. Pass Criteria

Release is ready when:

1. Verification handshake passes in SeaTalk.
2. Worker forwards non-verification events to backend.
3. Callback endpoint always ACKs quickly.
4. Chat and automation workflows both execute expected actions.
5. No forwarding loops and no secret files tracked in git.
