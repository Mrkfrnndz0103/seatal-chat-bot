# SeaTalk callback reference

Implemented endpoint:

- `POST /seatalk/callback`

Verification behavior follows `docs/callback.md`:

```json
{
  "event_type": "event_verification",
  "event": {
    "seatalk_challenge": "abc123"
  }
}
```

Response:

```json
{
  "seatalk_challenge": "abc123"
}
```

All other valid events return:

```json
{
  "ok": true,
  "queued": true
}
```

Events are acknowledged immediately and processed asynchronously by background workers.
