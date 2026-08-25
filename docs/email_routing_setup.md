# Cloudflare Email Routing + Cloudflare Worker Email-to-Upload Setup Guide

This guide explains how to set up Cloudflare Email Routing with a Cloudflare Worker to ingest documents emailed to your domain (e.g., `uploads@yourdomain.com`) directly into the FastAPI Document Management System (DMS).

---

## Architecture Overview

```
[User Email] ---> [Cloudflare MX / Email Routing]
                          |
                          v
                 [Cloudflare Worker]
                          | (HTTP POST + X-Webhook-Secret)
                          v
        [FastAPI DMS /api/v1/connectors/email-inbound]
                          |
                          v
       [connector_ingest_service (Hash & MinIO & DB)]
```

---

## 1. Cloudflare Email Routing Setup

1. **Enable Email Routing in Cloudflare**:
   - Navigate to your domain dashboard on [Cloudflare](https://dash.cloudflare.com).
   - Go to **Email** > **Email Routing**.
   - Enable Email Routing. Cloudflare will automatically prompt you to add required DNS records (`MX` and `TXT` SPF records).

2. **Add Routing Rule**:
   - In Cloudflare Dashboard, go to **Email** > **Email Routing** > **Routing rules**.
   - Click **Create rule**.
   - **Custom address**: Enter your desired ingestion address, e.g., `uploads@yourdomain.com` (or matching wildcard `*@yourdomain.com`).
   - **Action**: Select **Send to a Worker**.
   - **Destination**: Select your deployed Worker (`dms-email-router`).

---

## 2. Cloudflare Worker Deployment

The Worker code is located in `cloudflare-worker/`.

### Prerequisites
- Node.js (v18+) and `npm` installed.
- Cloudflare Wrangler CLI (`npm install -g wrangler` or `npx wrangler`).

### Deployment Steps

1. **Configure Environment Variables**:
   Update `cloudflare-worker/wrangler.jsonc` with your backend URL:
   ```jsonc
   {
     "name": "dms-email-router",
     "main": "src/index.js",
     "compatibility_date": "2024-09-23",
     "vars": {
       "BACKEND_URL": "https://dms.yourdomain.com"
     }
   }
   ```

2. **Set Webhook Secret**:
   Set the secret header value matching `EMAIL_WEBHOOK_SECRET` in your backend `.env` / `config.py`:
   ```bash
   cd cloudflare-worker
   npx wrangler secret put WEBHOOK_SECRET
   # Enter the secret value when prompted (e.g. change_me_webhook_secret)
   ```

3. **Deploy Worker**:
   ```bash
   npx wrangler deploy
   ```

---

## 3. Backend Configuration

Ensure the following settings are present in your backend `.env` file or `config.py`:

```env
EMAIL_WEBHOOK_ENABLED=true
EMAIL_WEBHOOK_SECRET=change_me_webhook_secret
```

The webhook endpoint is available at:
`POST /api/v1/connectors/email-inbound`

---

## 4. End-to-End Testing

### Option A: Direct Webhook Test (cURL)

Generate a Base64-encoded raw MIME sample and send it to your running FastAPI instance:

```bash
# 1. Create a raw MIME message file
cat << 'EOF' > /tmp/sample_email.eml
From: test@example.com
To: uploads@yourdomain.com
Subject: Sample Ingestion
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-Type: text/plain; charset="utf-8"

Please ingest attached document.

--BOUNDARY
Content-Type: text/plain; name="test_doc.txt"
Content-Disposition: attachment; filename="test_doc.txt"

Hello World DMS Ingestion Test Content
--BOUNDARY--
EOF

# 2. Base64 encode the MIME file
B64_DATA=$(base64 -w 0 /tmp/sample_email.eml)

# 3. Post to API webhook
curl -X POST http://localhost:8000/api/v1/connectors/email-inbound \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: change_me_webhook_secret" \
  -d "{\"raw_email_b64\": \"$B64_DATA\"}"
```

**Expected Response**:
```json
{
  "status": "success",
  "attachments_processed": 1,
  "attachments_ingested": 1,
  "attachments_skipped_duplicate": 0,
  "ingested_details": [
    {
      "filename": "test_doc.txt",
      "document_id": "...",
      "file_hash": "..."
    }
  ],
  "errors": []
}
```

### Option B: Real Email Test

1. Send an email with a file attachment (PDF, DOCX, CSV, etc.) to `uploads@yourdomain.com`.
2. Check Cloudflare Worker logs (`npx wrangler tail`) to observe email event reception.
3. Check FastAPI logs to observe ingestion.
4. Verify the document appears in your DMS document list!

---

## 5. Error Handling & Retries

- If the FastAPI backend endpoint returns a non-2xx status code or is temporarily unreachable, the Cloudflare Worker throws an error.
- Cloudflare Email Routing automatically retries email delivery when Worker execution fails, ensuring no emails are lost during temporary server downtime or maintenance.
