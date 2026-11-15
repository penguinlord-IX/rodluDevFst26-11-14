"""
interactive_map.py - Modular Interactive Map Component for GDG DevFest Hackathon.
Exports modular UI and script components so other modules (like gas_calculator.py)
can import and compose the map without duplicating code.

Can also be run standalone:
    python "interactive map.py"
"""

import sys
import json
import argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from route_service import calculate_distance, get_api_key

# 1. Modular Head Tags (Leaflet CSS and JS)
MAP_HEAD_TAGS = """
    <!-- Leaflet Interactive Maps CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
"""

# 2. Modular CSS Styles for the Interactive Map
MAP_STYLES = """
    .map-card {
        margin-top: 1.5rem;
        display: none;
        animation: fadeIn 0.4s ease;
    }

    .map-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 0.75rem;
    }

    .map-title-group h3 {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 0.25rem;
    }

    .map-actions {
        display: flex;
        gap: 0.5rem;
    }

    .btn-map-control {
        background: var(--input-bg);
        border: 1px solid var(--card-border);
        color: #E2E8F0;
        padding: 0.45rem 0.85rem;
        border-radius: 0.5rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        transition: all 0.2s ease;
    }

    .btn-map-control:hover {
        background: rgba(66, 133, 244, 0.15);
        border-color: var(--primary);
        color: #FFFFFF;
    }

    #route-map {
        width: 100%;
        height: 480px;
        border-radius: 0.85rem;
        border: 1px solid var(--card-border);
        background: #0B1120;
        z-index: 1;
    }

    .map-footer-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.85rem;
        font-size: 0.8rem;
        color: var(--text-muted);
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .map-legend {
        display: flex;
        gap: 1rem;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
    }

    .legend-dot.start { background: #4285F4; box-shadow: 0 0 6px #4285F4; }
    .legend-dot.end { background: #34A853; box-shadow: 0 0 6px #34A853; }
    .legend-dot.route { background: #60A5FA; box-shadow: 0 0 6px #60A5FA; }

    .leaflet-popup-content-wrapper {
        background: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #475569 !important;
        border-radius: 0.75rem !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5) !important;
    }

    .leaflet-popup-tip {
        background: #1E293B !important;
    }

    .leaflet-container {
        font-family: inherit;
    }
"""


def get_map_html() -> str:
    """Returns the HTML markup for the interactive map card component."""
    return """
        <!-- Interactive Route Map Card -->
        <div id="map-container-card" class="card map-card">
            <div class="map-header">
                <div class="map-title-group">
                    <span class="badge" style="margin-bottom: 0;">Interactive Map</span>
                    <h3 id="map-subtitle">Driving Route Preview</h3>
                </div>
                <div class="map-actions">
                    <button type="button" class="btn-map-control" onclick="recenterMap()" title="Re-center map to fit route">
                        🎯 Re-center
                    </button>
                    <a id="google-maps-link" href="#" target="_blank" rel="noopener" class="btn-map-control" title="Open directions in Google Maps">
                        Open in Google Maps ↗
                    </a>
                </div>
            </div>
            <div id="route-map"></div>
            <div class="map-footer-info">
                <span id="map-route-summary">Route calculated via Google Routes API</span>
                <span class="map-legend">
                    <span class="legend-item"><span class="legend-dot start"></span> Start (A)</span>
                    <span class="legend-item"><span class="legend-dot end"></span> Destination (B)</span>
                    <span class="legend-item"><span class="legend-dot route"></span> Driving Route</span>
                </span>
            </div>
        </div>
    """


def get_map_scripts() -> str:
    """Returns the JavaScript logic for polyline decoding, rendering, and map updates."""
    return """
        let map = null;
        let routeLayerGroup = null;
        let currentBounds = null;

        function decodePolyline(encoded) {
            if (!encoded) return [];
            let poly = [];
            let index = 0, len = encoded.length;
            let lat = 0, lng = 0;

            while (index < len) {
                let b, shift = 0, result = 0;
                do {
                    b = encoded.charCodeAt(index++) - 63;
                    result |= (b & 0x1f) << shift;
                    shift += 5;
                } while (b >= 0x20);
                let dlat = ((result & 1) !== 0 ? ~(result >> 1) : (result >> 1));
                lat += dlat;

                shift = 0;
                result = 0;
                do {
                    b = encoded.charCodeAt(index++) - 63;
                    result |= (b & 0x1f) << shift;
                    shift += 5;
                } while (b >= 0x20);
                let dlng = ((result & 1) !== 0 ? ~(result >> 1) : (result >> 1));
                lng += dlng;

                poly.push([lat / 1e5, lng / 1e5]);
            }
            return poly;
        }

        function initOrUpdateMap(data) {
            const mapCard = document.getElementById('map-container-card');

            // Hide map for manual mileage input without geographic coordinates
            if (!mapCard || data.mode === 'manual' || !data.origin_coords || !data.destination_coords) {
                if (mapCard) mapCard.style.display = 'none';
                return;
            }

            // Reveal map card
            mapCard.style.display = 'block';

            // Initialize Leaflet map instance on first display
            if (!map) {
                map = L.map('route-map', {
                    zoomControl: true,
                    attributionControl: true
                });

                L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
                    maxZoom: 19
                }).addTo(map);

                routeLayerGroup = L.layerGroup().addTo(map);
            }

            // Clear previous route layers to allow seamless dynamic updates
            routeLayerGroup.clearLayers();

            let latlngs = [];
            if (data.polyline) {
                latlngs = decodePolyline(data.polyline);
            }

            // Fallback straight line between coordinates if polyline is not available
            if (!latlngs.length && data.origin_coords && data.destination_coords) {
                latlngs = [
                    [data.origin_coords.lat, data.origin_coords.lng],
                    [data.destination_coords.lat, data.destination_coords.lng]
                ];
            }

            // Render driving route polyline
            if (latlngs.length > 0) {
                L.polyline(latlngs, {
                    color: '#4285F4',
                    weight: 8,
                    opacity: 0.35,
                    lineCap: 'round',
                    lineJoin: 'round'
                }).addTo(routeLayerGroup);

                L.polyline(latlngs, {
                    color: '#60A5FA',
                    weight: 4,
                    opacity: 0.95,
                    lineCap: 'round',
                    lineJoin: 'round'
                }).addTo(routeLayerGroup);
            }

            // Start Location Pin (A)
            if (data.origin_coords) {
                const startMarker = L.marker([data.origin_coords.lat, data.origin_coords.lng], {
                    icon: L.divIcon({
                        className: 'custom-map-marker',
                        html: '<div style="background:#4285F4; color:#fff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:12px; border:2px solid #fff; box-shadow:0 0 10px rgba(66,133,244,0.8);">A</div>',
                        iconSize: [28, 28],
                        iconAnchor: [14, 14],
                        popupAnchor: [0, -16]
                    })
                }).addTo(routeLayerGroup);

                startMarker.bindPopup(`
                    <div style="font-size:0.85rem; line-height:1.4;">
                        <strong style="color:#60A5FA;">Start Location (A)</strong><br>
                        ${escapeHtml(data.origin_formatted || data.origin_input)}
                    </div>
                `);
            }

            // Destination Pin (B)
            if (data.destination_coords) {
                const destMarker = L.marker([data.destination_coords.lat, data.destination_coords.lng], {
                    icon: L.divIcon({
                        className: 'custom-map-marker',
                        html: '<div style="background:#34A853; color:#fff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:12px; border:2px solid #fff; box-shadow:0 0 10px rgba(52,168,83,0.8);">B</div>',
                        iconSize: [28, 28],
                        iconAnchor: [14, 14],
                        popupAnchor: [0, -16]
                    })
                }).addTo(routeLayerGroup);

                destMarker.bindPopup(`
                    <div style="font-size:0.85rem; line-height:1.4;">
                        <strong style="color:#86EFAC;">Destination (B)</strong><br>
                        ${escapeHtml(data.destination_formatted || data.destination_input)}
                    </div>
                `);
            }

            // Fit bounds to frame pins and route
            if (latlngs.length > 0) {
                currentBounds = L.latLngBounds(latlngs);
                setTimeout(() => {
                    map.invalidateSize();
                    map.fitBounds(currentBounds, { padding: [50, 50], maxZoom: 15 });
                }, 150);
            }

            document.getElementById('map-subtitle').textContent =
                `${data.distance_miles} miles • Driving Time: ${data.duration_text || 'N/A'}`;

            const gmapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(data.origin_formatted || data.origin_input)}&destination=${encodeURIComponent(data.destination_formatted || data.destination_input)}`;
            document.getElementById('google-maps-link').href = gmapsUrl;

            // Smooth scroll down to reveal map
            setTimeout(() => {
                mapCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 250);
        }

        function recenterMap() {
            if (map && currentBounds) {
                map.fitBounds(currentBounds, { padding: [50, 50], maxZoom: 15 });
            }
        }
    """


def get_standalone_map_page() -> str:
    """Builds the complete standalone web page for testing interactive_map alone."""
    from trip_route import BASE_STYLES, get_trip_route_html, get_trip_route_scripts

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Route Map | GDG DevFest</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {MAP_HEAD_TAGS}
    <style>
        {BASE_STYLES}
        {MAP_STYLES}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Interactive Route Map</h1>
            <p>Driving route visualization with start & destination pins</p>
        </header>

        {get_trip_route_html()}
        {get_map_html()}

        <footer class="footer">
            Modular Gas Cost Calculator • Interactive Map Module • GDG DevFest Hackathon
        </footer>
    </div>

    <script>
        {get_trip_route_scripts()}
        {get_map_scripts()}
    </script>
</body>
</html>"""


class StandaloneMapRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for standalone map testing."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path in ("/", "/index.html"):
            content = get_standalone_map_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        from trip_route import handle_route_api
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path in ("/api/calculate", "/api/distance"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if body else {}
            result = handle_route_api(payload)
            response_body = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200 if result.get("success") else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        else:
            self.send_error(404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Interactive Route Map")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    args = parser.parse_args()

    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, StandaloneMapRequestHandler)
    print("=" * 60)
    print(" GDG DevFest - Standalone Interactive Map")
    print(f" Running at: http://{args.host}:{args.port}/")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        httpd.server_close()


if __name__ == "__main__":
    main()
