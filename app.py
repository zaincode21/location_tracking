import json
import os
import ssl
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
BASE_DIR = Path(__file__).parent
DATA_FILE = Path(os.getenv("IP_DATA_FILE", BASE_DIR / "ip_data.json"))
AUDIT_LOG_FILE = Path(os.getenv("AUDIT_LOG_FILE", BASE_DIR / "audit_logs.jsonl"))
TLS_CERT_FILE = os.getenv("TLS_CERT_FILE")
TLS_KEY_FILE = os.getenv("TLS_KEY_FILE")
EXAMPLE_IP = "2c0f:eb68:62a:b000:6f3c:fd9a:c6c7:c465"
IP_ACCURACY_METERS = 25000


# ---------------------------------------------------------------------------
# OpenAPI 3.0 specification
# ---------------------------------------------------------------------------

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Privacy-Safe Location Service",
        "description": (
            "Resolves device GPS coordinates (after user permission) or falls back "
            "to approximate IP-based geolocation. Logs consent events for auditing."
        ),
        "version": "1.0.0",
    },
    "servers": [{"url": "/"}],
    "tags": [
        {"name": "location", "description": "Location resolution endpoints"},
        {"name": "audit",    "description": "Consent audit log endpoints"},
        {"name": "system",   "description": "Service health"},
    ],
    "paths": {
        "/api/health": {
            "get": {
                "tags": ["system"],
                "summary": "Health check",
                "description": "Returns a simple status object confirming the service is running.",
                "operationId": "getHealth",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"},
                                "example": {
                                    "success": True,
                                    "service": "privacy-safe-location-service",
                                    "status": "ok",
                                },
                            }
                        },
                    }
                },
            }
        },
        "/api/location/ip": {
            "get": {
                "tags": ["location"],
                "summary": "Get approximate IP-based location",
                "description": (
                    "Returns city, region, country, latitude/longitude, and ISP info "
                    "derived from the example IP record in ip_data.json. "
                    "No user permission is required."
                ),
                "operationId": "getIpLocation",
                "responses": {
                    "200": {
                        "description": "Approximate location resolved",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ApproximateLocationResponse"}
                            }
                        },
                    },
                    "500": {
                        "description": "IP record not found or data file error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/location": {
            "post": {
                "tags": ["location"],
                "summary": "Submit precise GPS location",
                "description": (
                    "Accepts GPS coordinates obtained from the browser Geolocation API "
                    "after the user grants permission. Returns a structured location object."
                ),
                "operationId": "postGpsLocation",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/GpsLocationRequest"},
                            "example": {
                                "latitude": 37.7749,
                                "longitude": -122.4194,
                                "accuracy_meters": 10,
                                "altitude": None,
                                "heading": None,
                                "speed": None,
                                "timestamp": "2024-01-15T12:00:00.000Z",
                            },
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Precise location accepted",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PreciseLocationResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Missing required fields or invalid JSON",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/audit-logs": {
            "get": {
                "tags": ["audit"],
                "summary": "List audit log events",
                "description": "Returns all consent events stored in audit_logs.jsonl.",
                "operationId": "getAuditLogs",
                "responses": {
                    "200": {
                        "description": "Audit log entries",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AuditLogsResponse"}
                            }
                        },
                    }
                },
            },
            "post": {
                "tags": ["audit"],
                "summary": "Append an audit log event",
                "description": (
                    "Records a permission-granted or permission-denied consent event. "
                    "Called automatically by the browser UI when the user makes a decision."
                ),
                "operationId": "postAuditLog",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AuditLogRequest"},
                            "example": {
                                "event_type": "permission-granted",
                                "details": {"source": "browser-ui"},
                            },
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Event recorded",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AuditLogCreatedResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid event_type or malformed JSON",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            },
        },
    },
    "components": {
        "schemas": {
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "service": {"type": "string", "example": "privacy-safe-location-service"},
                    "status":  {"type": "string", "example": "ok"},
                },
            },
            "GpsLocationRequest": {
                "type": "object",
                "required": ["latitude", "longitude", "accuracy_meters"],
                "properties": {
                    "latitude":        {"type": "number", "format": "double", "example": 37.7749},
                    "longitude":       {"type": "number", "format": "double", "example": -122.4194},
                    "accuracy_meters": {"type": "number", "format": "double", "example": 10},
                    "altitude":        {"type": "number", "format": "double", "nullable": True},
                    "heading":         {"type": "number", "format": "double", "nullable": True},
                    "speed":           {"type": "number", "format": "double", "nullable": True},
                    "timestamp":       {"type": "string", "format": "date-time"},
                },
            },
            "PreciseLocationResponse": {
                "type": "object",
                "properties": {
                    "success":         {"type": "boolean"},
                    "label":           {"type": "string", "example": "Precise Location"},
                    "source":          {"type": "string", "example": "device-gps"},
                    "latitude":        {"type": "number"},
                    "longitude":       {"type": "number"},
                    "accuracy_meters": {"type": "number"},
                    "altitude":        {"type": "number", "nullable": True},
                    "heading":         {"type": "number", "nullable": True},
                    "speed":           {"type": "number", "nullable": True},
                    "timestamp":       {"type": "string", "format": "date-time"},
                    "message":         {"type": "string"},
                },
            },
            "ConnectionInfo": {
                "type": "object",
                "properties": {
                    "asn":    {"type": "string"},
                    "org":    {"type": "string"},
                    "isp":    {"type": "string"},
                    "domain": {"type": "string"},
                },
            },
            "ApproximateLocationResponse": {
                "type": "object",
                "properties": {
                    "success":         {"type": "boolean"},
                    "label":           {"type": "string", "example": "Approximate Location"},
                    "source":          {"type": "string", "example": "ip-geolocation"},
                    "ip":              {"type": "string"},
                    "city":            {"type": "string"},
                    "region":          {"type": "string"},
                    "country":         {"type": "string"},
                    "latitude":        {"type": "number"},
                    "longitude":       {"type": "number"},
                    "accuracy_meters": {"type": "number", "example": 25000},
                    "connection":      {"$ref": "#/components/schemas/ConnectionInfo"},
                    "timestamp":       {"type": "string", "format": "date-time"},
                    "message":         {"type": "string"},
                },
            },
            "AuditLogRequest": {
                "type": "object",
                "required": ["event_type"],
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": ["permission-granted", "permission-denied"],
                    },
                    "details": {"type": "object", "additionalProperties": True},
                },
            },
            "AuditLogEntry": {
                "type": "object",
                "properties": {
                    "id":         {"type": "string", "format": "date-time"},
                    "event_type": {"type": "string"},
                    "timestamp":  {"type": "string", "format": "date-time"},
                    "details":    {"type": "object", "additionalProperties": True},
                },
            },
            "AuditLogCreatedResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "event":   {"$ref": "#/components/schemas/AuditLogEntry"},
                },
            },
            "AuditLogsResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "logs": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/AuditLogEntry"},
                    },
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "message": {"type": "string"},
                },
            },
        }
    },
}


# ---------------------------------------------------------------------------
# Swagger UI page (loads spec from /api/openapi.json)
# ---------------------------------------------------------------------------

SWAGGER_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Location Service – API Docs</title>
    <link rel="stylesheet"
          href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({
        url: "/api/openapi.json",
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: "BaseLayout",
        deepLinking: true,
        tryItOutEnabled: true,
      });
    </script>
  </body>
</html>
"""


LOCATION_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Privacy-Safe Location Service</title>
    <style>
      :root {
        color-scheme: light;
        font-family: Arial, sans-serif;
      }
      body {
        background: #f6f7fb;
        color: #162033;
        margin: 0;
      }
      main {
        margin: 0 auto;
        max-width: 1100px;
        padding: 2rem;
      }
      .card {
        background: #fff;
        border: 1px solid #dfe4ee;
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(22, 32, 51, 0.06);
        margin-bottom: 1rem;
        padding: 1.25rem;
      }
      .grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      }
      .status {
        border-left: 5px solid #64748b;
      }
      .precise {
        border-left-color: #15803d;
      }
      .approximate {
        border-left-color: #b45309;
      }
      button {
        background: #1d4ed8;
        border: 0;
        border-radius: 8px;
        color: white;
        cursor: pointer;
        font-size: 1rem;
        padding: 0.8rem 1rem;
      }
      button.secondary {
        background: #475569;
      }
      table {
        border-collapse: collapse;
        width: 100%;
      }
      td, th {
        border-bottom: 1px solid #e2e8f0;
        padding: 0.65rem;
        text-align: left;
      }
      pre {
        background: #0f172a;
        border-radius: 10px;
        color: #e2e8f0;
        overflow: auto;
        padding: 1rem;
        white-space: pre-wrap;
      }
      iframe {
        border: 0;
        border-radius: 10px;
        height: 320px;
        width: 100%;
      }
      .muted {
        color: #64748b;
      }
    </style>
  </head>
  <body>
    <main>
      <section class="card">
        <h1>Location Service</h1>
        <p>
          This service follows browser and operating-system security rules.
          Precise GPS coordinates are requested only after you allow location
          permission. If permission is denied, the service falls back to
          approximate IP-based location.
        </p>
        <p class="muted">
          GPS coordinates cannot be accessed without user permission because
          browsers and operating systems protect precise location as private
          information.
        </p>
        <button id="requestLocation">Get my location</button>
        <button class="secondary" id="loadLogs">Load audit logs</button>
      </section>

      <section class="grid">
        <div class="card status" id="resultCard">
          <h2 id="locationLabel">Waiting</h2>
          <div id="summary">Click the button to start.</div>
        </div>
        <div class="card">
          <h2>Consent Status</h2>
          <div id="consentStatus">No decision stored yet.</div>
        </div>
      </section>

      <section class="card">
        <h2>Map Preview</h2>
        <div id="map">Location map appears here.</div>
      </section>

      <section class="card">
        <h2>GPS Accuracy vs IP Accuracy</h2>
        <table>
          <thead>
            <tr>
              <th>Method</th>
              <th>Label</th>
              <th>Accuracy</th>
              <th>Coordinates</th>
            </tr>
          </thead>
          <tbody id="dashboard">
            <tr>
              <td colspan="4">No location data yet.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card">
        <h2>API Response</h2>
        <pre id="rawOutput">{}</pre>
      </section>

      <section class="card">
        <h2>Audit Logs</h2>
        <pre id="auditLogs">Click "Load audit logs".</pre>
      </section>
    </main>

    <script>
      const requestButton = document.getElementById("requestLocation");
      const logsButton = document.getElementById("loadLogs");
      const resultCard = document.getElementById("resultCard");
      const locationLabel = document.getElementById("locationLabel");
      const summary = document.getElementById("summary");
      const consentStatus = document.getElementById("consentStatus");
      const map = document.getElementById("map");
      const dashboard = document.getElementById("dashboard");
      const rawOutput = document.getElementById("rawOutput");
      const auditLogs = document.getElementById("auditLogs");

      function nowIso() {
        return new Date().toISOString();
      }

      function saveConsent(status) {
        const payload = { status, timestamp: nowIso() };
        localStorage.setItem("locationConsent", JSON.stringify(payload));
        renderConsent();
        return payload;
      }

      function renderConsent() {
        const stored = localStorage.getItem("locationConsent");
        if (!stored) {
          consentStatus.textContent = "No decision stored yet.";
          return;
        }
        const payload = JSON.parse(stored);
        consentStatus.innerHTML = `
          <strong>${payload.status}</strong><br>
          <span class="muted">${payload.timestamp}</span>
        `;
      }

      async function readJsonResponse(response) {
        const body = await response.text();
        try {
          return JSON.parse(body);
        } catch (error) {
          throw new Error(
            `Expected JSON from ${response.url}, got HTTP ${response.status}: ${body.slice(0, 120)}`
          );
        }
      }

      async function postJson(url, payload) {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await readJsonResponse(response);
        if (!response.ok) {
          throw new Error(data.message || `Request failed with HTTP ${response.status}`);
        }
        return data;
      }

      async function logEvent(eventType, details) {
        return postJson("/api/audit-logs", {
          event_type: eventType,
          details
        });
      }

      function renderMap(latitude, longitude) {
        map.innerHTML = `
          <iframe
            title="Map preview"
            loading="lazy"
            src="https://www.openstreetmap.org/export/embed.html?bbox=${longitude - 0.02}%2C${latitude - 0.02}%2C${longitude + 0.02}%2C${latitude + 0.02}&layer=mapnik&marker=${latitude}%2C${longitude}">
          </iframe>
        `;
      }

      function renderDashboard(current, fallback) {
        const rows = [];
        if (current) {
          rows.push(`
            <tr>
              <td>${current.source}</td>
              <td>${current.label}</td>
              <td>${Math.round(current.accuracy_meters).toLocaleString()} meters</td>
              <td>${current.latitude}, ${current.longitude}</td>
            </tr>
          `);
        }
        if (fallback) {
          rows.push(`
            <tr>
              <td>${fallback.source}</td>
              <td>${fallback.label}</td>
              <td>${Math.round(fallback.accuracy_meters).toLocaleString()} meters</td>
              <td>${fallback.latitude}, ${fallback.longitude}</td>
            </tr>
          `);
        }
        dashboard.innerHTML = rows.join("");
      }

      function renderLocation(payload, fallback = null) {
        const isPrecise = payload.label === "Precise Location";
        resultCard.className = `card status ${isPrecise ? "precise" : "approximate"}`;
        locationLabel.textContent = payload.label;
        summary.innerHTML = `
          <p><strong>Latitude:</strong> ${payload.latitude}</p>
          <p><strong>Longitude:</strong> ${payload.longitude}</p>
          <p><strong>Accuracy:</strong> ${Math.round(payload.accuracy_meters).toLocaleString()} meters</p>
          <p><strong>Timestamp:</strong> ${payload.timestamp}</p>
          ${payload.city ? `<p><strong>City:</strong> ${payload.city}, ${payload.region}, ${payload.country}</p>` : ""}
          ${payload.connection ? `<p><strong>ISP:</strong> ${payload.connection.isp}</p>` : ""}
        `;
        renderMap(payload.latitude, payload.longitude);
        renderDashboard(payload, fallback);
        rawOutput.textContent = JSON.stringify(payload, null, 2);
      }

      async function getIpLocation() {
        const response = await fetch("/api/location/ip");
        const data = await readJsonResponse(response);
        if (!response.ok) {
          throw new Error(data.message || `Request failed with HTTP ${response.status}`);
        }
        return data;
      }

      async function sendGpsLocation(position) {
        return postJson("/api/location", {
          source: "gps",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_meters: position.coords.accuracy,
          altitude: position.coords.altitude,
          heading: position.coords.heading,
          speed: position.coords.speed,
          timestamp: new Date(position.timestamp).toISOString()
        });
      }

      async function useIpFallback(reason) {
        const consent = saveConsent("denied");
        await logEvent("permission-denied", { reason, consent });
        const approximate = await getIpLocation();
        renderLocation(approximate);
      }

      requestButton.addEventListener("click", async () => {
        try {
          if (!window.isSecureContext) {
            summary.textContent = "Warning: geolocation requires HTTPS in production. Localhost is allowed for development.";
          }

          if (!navigator.geolocation) {
            await useIpFallback("Geolocation is not supported by this browser.");
            return;
          }

          summary.textContent = "Requesting GPS permission...";
          navigator.geolocation.getCurrentPosition(
            async (position) => {
              try {
                const consent = saveConsent("granted");
                await logEvent("permission-granted", { consent });
                const precise = await sendGpsLocation(position);
                const approximate = await getIpLocation();
                renderLocation(precise, approximate);
              } catch (error) {
                summary.textContent = error.message;
              }
            },
            async (error) => {
              try {
                await useIpFallback(error.message);
              } catch (fallbackError) {
                summary.textContent = fallbackError.message;
              }
            },
            {
              enableHighAccuracy: true,
              timeout: 15000,
              maximumAge: 0
            }
          );
        } catch (error) {
          summary.textContent = error.message;
        }
      });

      logsButton.addEventListener("click", async () => {
        try {
          const response = await fetch("/api/audit-logs");
          const payload = await readJsonResponse(response);
          if (!response.ok) {
            throw new Error(payload.message || `Request failed with HTTP ${response.status}`);
          }
          auditLogs.textContent = JSON.stringify(payload, null, 2);
        } catch (error) {
          auditLogs.textContent = error.message;
        }
      });

      renderConsent();
    </script>
  </body>
</html>
"""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def render_location_page():
    return LOCATION_HTML


def build_precise_location(payload):
    required_fields = ("latitude", "longitude", "accuracy_meters")
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        raise ValueError(f"Missing fields: {', '.join(missing_fields)}")

    return {
        "success": True,
        "label": "Precise Location",
        "source": "device-gps",
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "accuracy_meters": payload["accuracy_meters"],
        "altitude": payload.get("altitude"),
        "heading": payload.get("heading"),
        "speed": payload.get("speed"),
        "timestamp": payload.get("timestamp") or utc_now(),
        "message": "GPS coordinates were provided after user permission.",
    }


def build_ip_location():
    records = load_ip_data()
    record = records.get(EXAMPLE_IP)
    if not record:
        raise RuntimeError(f"IP record not found for {EXAMPLE_IP}")

    connection = record.get("connection") or {}
    return {
        "success": True,
        "label": "Approximate Location",
        "source": "ip-geolocation",
        "ip": EXAMPLE_IP,
        "city": record.get("city"),
        "region": record.get("region"),
        "country": record.get("country"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "accuracy_meters": IP_ACCURACY_METERS,
        "connection": {
            "asn": connection.get("asn"),
            "org": connection.get("org"),
            "isp": connection.get("isp"),
            "domain": connection.get("domain"),
        },
        "timestamp": utc_now(),
        "message": (
            "Approximate IP-based location. Precise GPS coordinates require "
            "browser location permission."
        ),
    }


def append_audit_log(event_type, details=None):
    event = {
        "id": utc_now(),
        "event_type": event_type,
        "timestamp": utc_now(),
        "details": details or {},
    }
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")
    return event


def read_audit_logs():
    if not AUDIT_LOG_FILE.exists():
        return []

    logs = []
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


def load_ip_data():
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(f"Local data file not found: {DATA_FILE}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Local data file contains invalid JSON: {DATA_FILE}") from error

    if not isinstance(data, dict):
        raise RuntimeError("Local data file must contain a JSON object")

    return data


def normalize_path(path):
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


class LocationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = normalize_path(urlparse(self.path).path)

        if path in ("/", "/my-location"):
            self._send_html(render_location_page())
            return

        if path == "/docs":
            self._send_html(SWAGGER_HTML)
            return

        if path == "/api/openapi.json":
            self._send_json(OPENAPI_SPEC)
            return

        if path == "/api/health":
            self._send_json(
                {
                    "success": True,
                    "service": "privacy-safe-location-service",
                    "status": "ok",
                }
            )
            return

        if path == "/api/location/ip":
            self._handle_ip_location()
            return

        if path == "/api/audit-logs":
            self._send_json({"success": True, "logs": read_audit_logs()})
            return

        self._send_json(
            {"success": False, "message": "Not found."},
            status_code=404,
        )

    def do_POST(self):
        path = normalize_path(urlparse(self.path).path)

        if path == "/api/location":
            self._handle_precise_location()
            return

        if path == "/api/audit-logs":
            self._handle_audit_log()
            return

        self._send_json(
            {"success": False, "message": "Not found."},
            status_code=404,
        )

    def _handle_ip_location(self):
        try:
            location = build_ip_location()
            self._send_json(location)
        except RuntimeError as error:
            self._send_json(
                {"success": False, "message": str(error)},
                status_code=500,
            )

    def _handle_precise_location(self):
        try:
            location = build_precise_location(self._read_json_body())
            self._send_json(location)
        except ValueError as error:
            self._send_json(
                {"success": False, "message": str(error)},
                status_code=400,
            )

    def _handle_audit_log(self):
        try:
            payload = self._read_json_body()
        except ValueError as error:
            self._send_json(
                {"success": False, "message": str(error)},
                status_code=400,
            )
            return

        event_type = payload.get("event_type")
        if event_type not in {"permission-granted", "permission-denied"}:
            self._send_json(
                {
                    "success": False,
                    "message": "event_type must be permission-granted or permission-denied",
                },
                status_code=400,
            )
            return

        event = append_audit_log(event_type, payload.get("details"))
        self._send_json({"success": True, "event": event}, status_code=201)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            raise ValueError("Request body is required")

        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise ValueError("Request body must be valid JSON") from error

    def _send_json(self, payload, status_code=200):
        body = json.dumps(payload, indent=2).encode("utf-8")

        self.send_response(status_code)
        self._send_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status_code=200):
        body = html.encode("utf-8")

        self.send_response(status_code)
        self._send_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "geolocation=(self)")
        self.send_header("Cache-Control", "no-store")

    def log_message(self, format, *args):
        return


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def run_server():
    server = ReusableHTTPServer((HOST, PORT), LocationHandler)
    protocol = "http"

    if TLS_CERT_FILE and TLS_KEY_FILE:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(TLS_CERT_FILE, TLS_KEY_FILE)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    base_url = f"{protocol}://{HOST}:{PORT}"
    print(f"Location service running at {base_url}/my-location")
    print(f"Swagger UI (API docs):       {base_url}/docs")
    print(f"OpenAPI spec (JSON):         {base_url}/api/openapi.json")
    print(f"IP fallback endpoint:        {base_url}/api/location/ip")
    print(f"Audit logs endpoint:         {base_url}/api/audit-logs")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
