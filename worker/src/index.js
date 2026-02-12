export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/healthz") {
      return json({ status: "ok", runtime: "cloudflare-worker" }, 200);
    }

    if (request.method !== "POST" || url.pathname !== "/seatalk/callback") {
      return new Response("", { status: 405 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("", { status: 400 });
    }

    const eventType = body?.event_type;
    const challenge = body?.event?.seatalk_challenge;

    // SeaTalk event verification contract.
    if (eventType === "event_verification" && challenge) {
      return json({ seatalk_challenge: challenge }, 200);
    }

    const targetBase = (env.BOT_SERVER_URL || "").trim();
    if (!targetBase) {
      return json({ ok: true, warning: "BOT_SERVER_URL is not configured" }, 200);
    }
    const targetUrl = new URL(targetBase);
    if (targetUrl.host === url.host) {
      return json(
        {
          ok: false,
          error: "invalid_bot_server_url",
          detail: "BOT_SERVER_URL points to this Worker host and would cause a forwarding loop.",
        },
        500
      );
    }

    const upstream = `${targetBase.replace(/\/$/, "")}/seatalk/callback`;
    const headers = new Headers({ "Content-Type": "application/json" });

    const signature = request.headers.get("Signature");
    if (signature) {
      headers.set("Signature", signature);
    }

    try {
      const response = await fetch(upstream, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        return json({ ok: false, error: "upstream_failed", status: response.status }, 502);
      }

      return json({ ok: true }, 200);
    } catch (err) {
      return json({ ok: false, error: "upstream_unreachable", detail: String(err) }, 502);
    }
  },
};

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
