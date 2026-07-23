package locationclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const defaultTimeout = 10 * time.Second

// Client talks to the privacy-safe location HTTP API.
type Client struct {
	baseURL    string
	httpClient *http.Client
}

// Option configures a Client.
type Option func(*Client)

// WithHTTPClient sets a custom HTTP client.
func WithHTTPClient(c *http.Client) Option {
	return func(cl *Client) {
		if c != nil {
			cl.httpClient = c
		}
	}
}

// WithTimeout sets the HTTP client timeout (ignored if WithHTTPClient was used).
func WithTimeout(d time.Duration) Option {
	return func(cl *Client) {
		cl.httpClient.Timeout = d
	}
}

// New creates a client for the location service.
// baseURL examples: "http://127.0.0.1:8001", "https://your-service.onrender.com"
func New(baseURL string, opts ...Option) *Client {
	cl := &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: defaultTimeout,
		},
	}
	for _, opt := range opts {
		opt(cl)
	}
	return cl
}

// Health calls GET /api/health.
func (c *Client) Health(ctx context.Context) (*HealthResponse, error) {
	var out HealthResponse
	if err := c.do(ctx, http.MethodGet, "/api/health", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetIPLocation calls GET /api/location/ip (approximate / IP-based location).
func (c *Client) GetIPLocation(ctx context.Context) (*Location, error) {
	var out Location
	if err := c.do(ctx, http.MethodGet, "/api/location/ip", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// SubmitGPS calls POST /api/location with device GPS coordinates.
func (c *Client) SubmitGPS(ctx context.Context, req GPSRequest) (*Location, error) {
	var out Location
	if err := c.do(ctx, http.MethodPost, "/api/location", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// PostAuditLog calls POST /api/audit-logs.
func (c *Client) PostAuditLog(ctx context.Context, req AuditLogRequest) (*AuditLogCreatedResponse, error) {
	var out AuditLogCreatedResponse
	if err := c.do(ctx, http.MethodPost, "/api/audit-logs", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetAuditLogs calls GET /api/audit-logs.
func (c *Client) GetAuditLogs(ctx context.Context) (*AuditLogsResponse, error) {
	var out AuditLogsResponse
	if err := c.do(ctx, http.MethodGet, "/api/audit-logs", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) do(ctx context.Context, method, path string, body any, out any) error {
	var reader io.Reader
	if body != nil {
		raw, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		reader = bytes.NewReader(raw)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reader)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request %s %s: %w", method, path, err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var errBody struct {
			Message string `json:"message"`
		}
		_ = json.Unmarshal(raw, &errBody)
		return &APIError{StatusCode: resp.StatusCode, Message: errBody.Message}
	}

	if out == nil {
		return nil
	}
	if err := json.Unmarshal(raw, out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	return nil
}
