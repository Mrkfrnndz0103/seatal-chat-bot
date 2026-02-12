// Cloudflare Worker for backlogs_update
// - Downloads ZIP from Google Drive
// - Streams unzip + CSV parse (fflate)
// - Filters rows (receiver_type=station, current_station=soc 5)
// - Sends filtered rows to FastAPI webhook
//
// Env vars:
// GOOGLE_CLIENT_EMAIL
// GOOGLE_PRIVATE_KEY (PEM, with \\n)
// BACKLOGS_DRIVE_FOLDER_ID
// FASTAPI_WEBHOOK_URL (e.g., https://your-host/webhook/backlogs_update_filtered)
// FASTAPI_WEBHOOK_TOKEN (optional)
// MAX_ROW_COUNT (optional)

import { Unzip } from "fflate";

async function getAccessToken(env) {
  const now = Math.floor(Date.now() / 1000);
  const header = {
    alg: "RS256",
    typ: "JWT",
  };
  const claimSet = {
    iss: env.GOOGLE_CLIENT_EMAIL,
    scope: "https://www.googleapis.com/auth/drive.readonly",
    aud: "https://oauth2.googleapis.com/token",
    exp: now + 3600,
    iat: now,
  };

  const enc = new TextEncoder();
  const b64 = (obj) =>
    btoa(String.fromCharCode(...enc.encode(JSON.stringify(obj))))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");

  const jwtUnsigned = `${b64(header)}.${b64(claimSet)}`;
  const keyPem = env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, "\n");
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToArrayBuffer(keyPem),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    enc.encode(jwtUnsigned)
  );
  const jwt = `${jwtUnsigned}.${arrayBufferToBase64Url(signature)}`;

  const body = new URLSearchParams();
  body.set("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer");
  body.set("assertion", jwt);

  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  const data = await resp.json();
  if (!data.access_token) {
    throw new Error("Failed to get access token");
  }
  return data.access_token;
}

function pemToArrayBuffer(pem) {
  const b64 = pem
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\s+/g, "");
  const raw = atob(b64);
  const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
  return buf.buffer;
}

function arrayBufferToBase64Url(buf) {
  const bytes = new Uint8Array(buf);
  let binary = "";
  for (let b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

async function downloadDriveZip(fileId, token) {
  const url = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    throw new Error(`Drive download failed: ${resp.status}`);
  }
  return resp.body;
}

function normalizeLine(line) {
  return line.replace(/\u0000/g, "").trim();
}

async function streamZipAndFilter(zipStream, maxRows) {
  const decoder = new TextDecoder("utf-8");
  const rows = [];
  const unzip = new Unzip((file) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      file.ondata = () => {};
      return;
    }

    let header = [];
    let buffer = "";
    file.ondata = (err, data, final) => {
      if (err) throw err;
      buffer += decoder.decode(data, { stream: !final });

      let idx;
      while ((idx = buffer.indexOf("\n")) >= 0) {
        const line = normalizeLine(buffer.slice(0, idx));
        buffer = buffer.slice(idx + 1);
        if (!line) continue;

        const cols = line.split(",");
        if (header.length === 0) {
          header = cols.map((h) => h.replace(/^\ufeff/, "").trim());
          continue;
        }

        const obj = {};
        for (let i = 0; i < header.length; i++) obj[header[i]] = cols[i] ?? "";

        const rt = (obj["Receiver type"] || "").trim().toLowerCase();
        const cs = (obj["Current Station"] || "").trim().toLowerCase();
        if (rt === "station" && cs === "soc 5") {
          rows.push([
            obj["TO Number"] || "",
            obj["SPX Tracking Number"] || "",
            obj["Receiver Name"] || "",
            obj["TO Order Quantity"] || "",
            obj["Operator"] || "",
            obj["Create Time"] || "",
            obj["Complete Time"] || "",
            obj["Remark"] || "",
            obj["Receive Status"] || "",
            obj["Staging Area ID"] || "",
          ]);
          if (rows.length >= maxRows) return;
        }
      }
    };
  });

  const reader = zipStream.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    unzip.push(value, false);
  }
  unzip.push(new Uint8Array(0), true);
  return rows;
}

async function sendToFastAPI(env, rows, fileId) {
  const body = {
    file_id: fileId,
    rows,
  };
  const headers = { "Content-Type": "application/json" };
  if (env.FASTAPI_WEBHOOK_TOKEN) {
    headers["x-webhook-token"] = env.FASTAPI_WEBHOOK_TOKEN;
  }
  const resp = await fetch(env.FASTAPI_WEBHOOK_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`FastAPI webhook failed: ${resp.status}`);
  }
  return resp.json();
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }
    const payload = await request.json();
    const fileId = payload.file_id || payload.id;
    if (!fileId) {
      return new Response("file_id required", { status: 400 });
    }

    const token = await getAccessToken(env);
    const zipStream = await downloadDriveZip(fileId, token);
    const maxRows = Number(env.MAX_ROW_COUNT || 500000);
    const rows = await streamZipAndFilter(zipStream, maxRows);
    const result = await sendToFastAPI(env, rows, fileId);
    return new Response(JSON.stringify(result), {
      headers: { "Content-Type": "application/json" },
    });
  },
};
