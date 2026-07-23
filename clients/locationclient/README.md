# locationclient (Go)

HTTP client for the privacy-safe location service. Use this from a **Go backend** so your app talks to the Python API over HTTP.

## Install in your Go project

```bash
# From this repo (local replace), or copy the package into your module.
go get github.com/zaincode21/location_tracking/clients/locationclient@latest
```

Or copy `clients/locationclient` into your repo and change the module path.

## Usage

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/zaincode21/location_tracking/clients/locationclient"
)

func main() {
	client := locationclient.New(
		"https://<your-service>.onrender.com", // or http://127.0.0.1:8001
		locationclient.WithTimeout(10*time.Second),
	)
	ctx := context.Background()

	if _, err := client.Health(ctx); err != nil {
		log.Fatal(err)
	}

	// Backend-only: approximate IP-based location
	loc, err := client.GetIPLocation(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(loc.Latitude, loc.Longitude, loc.City)

	// Optional: if your API already received GPS from a mobile/web client
	precise, err := client.SubmitGPS(ctx, locationclient.GPSRequest{
		Latitude:       -1.97,
		Longitude:      30.10,
		AccuracyMeters: 12,
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(precise.Label, precise.Latitude, precise.Longitude)
}
```

## Methods

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `Health` | `GET /api/health` | Liveness |
| `GetIPLocation` | `GET /api/location/ip` | Approximate location |
| `SubmitGPS` | `POST /api/location` | Forward GPS coords |
| `PostAuditLog` | `POST /api/audit-logs` | Consent event |
| `GetAuditLogs` | `GET /api/audit-logs` | List events |

## Notes

- `GetIPLocation` currently returns the **sample** IP record from the Python service (`ip_data.json`), not the caller's real IP.
- Precise GPS still has to come from a device; Go only forwards numbers via `SubmitGPS`.
