# Location Service

Privacy-safe location service for learning how browser GPS permission and
IP-based fallback work.

## Run

```bash
PORT=8001 python3 app.py
```

Open:

```text
http://127.0.0.1:8001/my-location
```

## What It Does

- Requests browser permission for precise GPS coordinates.
- Shows **Precise Location** when permission is granted.
- Falls back to **Approximate Location** from `ip_data.json` when permission is denied.
- Displays latitude, longitude, accuracy, timestamp, and a map preview.
- Stores consent status and timestamp in browser `localStorage`.
- Logs permission granted/denied events in `audit_logs.jsonl`.
- Shows a dashboard comparing GPS accuracy and IP-based accuracy.

## API Endpoints

```text
GET  /my-location
POST /api/location
GET  /api/location/ip
POST /api/audit-logs
GET  /api/audit-logs
```

## Go backend client

A ready-to-use HTTP client lives in [`clients/locationclient`](clients/locationclient).

```go
client := locationclient.New("https://<your-service>.onrender.com")
loc, err := client.GetIPLocation(context.Background())
```

See that package README for full usage.

## Deploy on Render

1. Push this repo to GitHub (remote: `location_tracking`).
2. In the [Render Dashboard](https://dashboard.render.com/), click **New +** → **Blueprint**.
3. Connect the GitHub repo. Render reads `render.yaml` and creates the web service.
4. After deploy, open `https://<your-service>.onrender.com/my-location`.

Render sets `PORT` automatically and terminates HTTPS at the edge, so browser geolocation works on the public URL.

**Notes for production:**

- Audit logs are written to `audit_logs.jsonl` on the instance disk; they reset when the service redeploys.
- IP fallback uses the sample record in `ip_data.json` (not the visitor's real IP).

### Troubleshooting API 404 errors

If the browser shows `404` on `/api/location/ip` and `Unexpected token 'N', "Not Found"`:

1. The request is **not reaching this Python app**. Our API always returns JSON, never plain text `Not Found`.
2. Verify the service type is **Web Service** (not Static Site).
3. Verify **Start Command** is `python app.py` and **Runtime** is Python.
4. Open `https://<your-service>.onrender.com/api/health` — you should see:

```json
{"success": true, "service": "privacy-safe-location-service", "status": "ok"}
```

If that URL returns HTML, plain text, or a different app, you are on the wrong Render service or the wrong repo is connected.

## HTTPS

For local development, browsers allow geolocation on `127.0.0.1`.

For deployment, use HTTPS. You can start the server with a certificate:

```bash
PORT=8443 TLS_CERT_FILE=cert.pem TLS_KEY_FILE=key.pem python3 app.py
```

Then open `https://127.0.0.1:8443/my-location`.
