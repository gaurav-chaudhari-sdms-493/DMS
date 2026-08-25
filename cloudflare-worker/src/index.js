/**
 * Cloudflare Worker for Email Routing -> DMS Inbound Webhook
 *
 * Catches incoming emails via Cloudflare Email Routing, converts the raw RFC822
 * message stream to Base64, and forwards it to the DMS FastAPI backend webhook endpoint.
 */

export default {
  /**
   * Cloudflare Email Routing Event Handler
   * @param {import("@cloudflare/workers-types").EmailMessage} message 
   * @param {Object} env 
   * @param {Object} ctx 
   */
  async email(message, env, ctx) {
    const backendUrl = env.BACKEND_URL || "https://dms.yourdomain.com";
    const webhookSecret = env.WEBHOOK_SECRET;

    if (!webhookSecret) {
      console.error("WEBHOOK_SECRET environment variable is not configured in Worker.");
      message.setReject("Internal server configuration error");
      return;
    }

    try {
      // 1. Read raw email stream into ArrayBuffer
      const rawResponse = new Response(message.raw);
      const arrayBuffer = await rawResponse.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);

      // 2. Convert bytes to Base64 string (chunked to avoid stack overflow)
      let binary = "";
      const len = bytes.byteLength;
      const chunkSize = 0x8000; // 32KB chunks
      for (let i = 0; i < len; i += chunkSize) {
        binary += String.fromCharCode.apply(
          null,
          bytes.subarray(i, Math.min(i + chunkSize, len))
        );
      }
      const rawEmailB64 = btoa(binary);

      // 3. Forward to FastAPI DMS Webhook
      const targetEndpoint = `${backendUrl.replace(/\/+$/, "")}/api/v1/connectors/email-inbound`;
      console.log(`Forwarding email from ${message.from} to ${message.to} -> ${targetEndpoint}`);

      const response = await fetch(targetEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Webhook-Secret": webhookSecret,
        },
        body: JSON.stringify({
          raw_email_b64: rawEmailB64,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Backend returned HTTP ${response.status}: ${errorText}`);
        // Re-throw error so Cloudflare Email Routing knows delivery failed and will attempt retry
        throw new Error(`Backend webhook failed with HTTP ${response.status}`);
      }

      const result = await response.json();
      console.log(`Email successfully ingested: ${JSON.stringify(result)}`);
    } catch (err) {
      console.error(`Error processing email message: ${err.message}`);
      // Throw error to notify Cloudflare Email Routing of delivery failure
      throw err;
    }
  },
};
