package locationclient_test

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/zaincode21/location_tracking/clients/locationclient"
)

// Example shows the usual backend-only flow: health check + IP location.
func Example() {
	baseURL := os.Getenv("LOCATION_API_URL")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8001"
	}

	client := locationclient.New(baseURL, locationclient.WithTimeout(8*time.Second))
	ctx := context.Background()

	health, err := client.Health(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(health.Status)

	loc, err := client.GetIPLocation(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("%s: %.6f, %.6f (%s)\n", loc.Label, loc.Latitude, loc.Longitude, loc.City)
}
