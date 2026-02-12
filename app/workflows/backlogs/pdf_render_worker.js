// Cloudflare Worker: PDF -> PNG renderer (first page)
// Requires Cloudflare Browser Rendering (paid add-on).
//
// Request: POST PDF bytes
// Response: { "png_base64": "..." }
//
// Env:
//  BROWSER_RENDERING_TOKEN
//  RENDER_VIEWPORT_WIDTH (optional)
//  RENDER_VIEWPORT_HEIGHT (optional)

import puppeteer from "@cloudflare/puppeteer";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const pdfBytes = await request.arrayBuffer();
    const b64 = btoa(String.fromCharCode(...new Uint8Array(pdfBytes)));
    const dataUrl = `data:application/pdf;base64,${b64}`;

    const browser = await puppeteer.launch(env.BROWSER_RENDERING_TOKEN);
    const page = await browser.newPage();

    const width = Number(env.RENDER_VIEWPORT_WIDTH || 1200);
    const height = Number(env.RENDER_VIEWPORT_HEIGHT || 1600);
    await page.setViewport({ width, height });

    await page.goto(dataUrl, { waitUntil: "networkidle0" });

    // Render first page only
    const pngBuffer = await page.screenshot({ type: "png", fullPage: true });
    await browser.close();

    const pngBase64 = btoa(String.fromCharCode(...new Uint8Array(pngBuffer)));
    return new Response(JSON.stringify({ png_base64: pngBase64 }), {
      headers: { "Content-Type": "application/json" },
    });
  },
};
