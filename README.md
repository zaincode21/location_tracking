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

## HTTPS

For local development, browsers allow geolocation on `127.0.0.1`.

For deployment, use HTTPS. You can start the server with a certificate:

```bash
PORT=8443 TLS_CERT_FILE=cert.pem TLS_KEY_FILE=key.pem python3 app.py
```

Then open `https://127.0.0.1:8443/my-location`.
