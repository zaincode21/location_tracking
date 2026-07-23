package locationclient

// HealthResponse is returned by GET /api/health.
type HealthResponse struct {
	Success bool   `json:"success"`
	Service string `json:"service"`
	Status  string `json:"status"`
}

// ConnectionInfo is ISP metadata on approximate location responses.
type ConnectionInfo struct {
	ASN    any    `json:"asn"`
	Org    string `json:"org"`
	ISP    string `json:"isp"`
	Domain string `json:"domain"`
}

// Location is the shared shape for precise and approximate location payloads.
type Location struct {
	Success         bool            `json:"success"`
	Label           string          `json:"label"`
	Source          string          `json:"source"`
	IP              string          `json:"ip,omitempty"`
	City            string          `json:"city,omitempty"`
	Region          string          `json:"region,omitempty"`
	Country         string          `json:"country,omitempty"`
	Latitude        float64         `json:"latitude"`
	Longitude       float64         `json:"longitude"`
	AccuracyMeters  float64         `json:"accuracy_meters"`
	Altitude        *float64        `json:"altitude,omitempty"`
	Heading         *float64        `json:"heading,omitempty"`
	Speed           *float64        `json:"speed,omitempty"`
	Connection      *ConnectionInfo `json:"connection,omitempty"`
	Timestamp       string          `json:"timestamp"`
	Message         string          `json:"message"`
}

// GPSRequest is the body for POST /api/location.
type GPSRequest struct {
	Latitude       float64  `json:"latitude"`
	Longitude      float64  `json:"longitude"`
	AccuracyMeters float64  `json:"accuracy_meters"`
	Altitude       *float64 `json:"altitude,omitempty"`
	Heading        *float64 `json:"heading,omitempty"`
	Speed          *float64 `json:"speed,omitempty"`
	Timestamp      string   `json:"timestamp,omitempty"`
}

// AuditLogRequest is the body for POST /api/audit-logs.
type AuditLogRequest struct {
	EventType string `json:"event_type"` // "permission-granted" or "permission-denied"
	Details   any    `json:"details,omitempty"`
}

// AuditEvent is a single stored consent event.
type AuditEvent struct {
	ID        string `json:"id"`
	EventType string `json:"event_type"`
	Timestamp string `json:"timestamp"`
	Details   any    `json:"details"`
}

// AuditLogCreatedResponse is returned by POST /api/audit-logs.
type AuditLogCreatedResponse struct {
	Success bool       `json:"success"`
	Event   AuditEvent `json:"event"`
}

// AuditLogsResponse is returned by GET /api/audit-logs.
type AuditLogsResponse struct {
	Success bool         `json:"success"`
	Logs    []AuditEvent `json:"logs"`
}

// APIError is returned when the service responds with a non-2xx JSON error body.
type APIError struct {
	StatusCode int
	Message    string
}

func (e *APIError) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return "location service request failed"
}
