"""
gas_calculator.py - Unified Coordinator for the GDG DevFest Gas Cost Calculator.
Imports and orchestrates modular components:
  1. trip_route: Route and distance calculation
  2. interactive_map: Leaflet driving route map visualization
  3. mpg: Vehicle fuel efficiency input
  4. gas_prices: Regional average gas price API collector
  5. final_computation: Final trip cost calculation and display

Can be run directly:
    python "gas calculator.py"
    python gas_calculator.py --cli
"""

import sys
import json
import argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# 1. Import Trip Route & Distance component and API controller
from trip_route import (
    BASE_STYLES,
    get_trip_route_html,
    get_trip_route_scripts,
    handle_route_api,
    run_cli_mode
)

# 2. Import Interactive Map component
from interactive_map import (
    MAP_HEAD_TAGS,
    MAP_STYLES,
    get_map_html,
    get_map_scripts
)

# 3. Import Vehicle Fuel Efficiency (MPG) component
from mpg import (
    MPG_STYLES,
    get_mpg_html,
    get_mpg_scripts,
    validate_mpg_input
)

# 4. Import Gas Prices regional collector component
from gas_prices import (
    GAS_PRICES_STYLES,
    get_gas_prices_html,
    get_gas_prices_scripts,
    get_gas_price_for_zip
)

# 5. Import Final Cost Computation component
from final_computation import (
    COMPUTATION_STYLES,
    get_computation_html,
    get_computation_scripts,
    calculate_trip_gas_cost,
    compute_trip_pipeline
)

# Shared configuration
from route_service import get_api_key


def build_unified_gas_calculator_page() -> str:
    """
    Composes the unified Web UI by assembling the modular sections together.
    No code duplication: imports HTML and JS directly from modular components.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gas Calculator | GDG DevFest</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {MAP_HEAD_TAGS}
    <style>
        {BASE_STYLES}
        {MAP_STYLES}
        {MPG_STYLES}
        {GAS_PRICES_STYLES}
        {COMPUTATION_STYLES}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Gas Cost Calculator</h1>
            <p>Compute trip route distance, view interactive maps, and calculate road travel gas costs</p>
        </header>

        <!-- Section 1: Modular Trip Route & Distance Component -->
        {get_trip_route_html()}

        <!-- Section 2: Modular Interactive Map Component -->
        {get_map_html()}

        <!-- Section 3: Modular Vehicle MPG Input Component -->
        {get_mpg_html()}

        <!-- Section 4: Modular Final Trip Cost Computation Component -->
        {get_computation_html()}

        <footer class="footer">
            Modular Gas Cost Calculator • GDG DevFest Hackathon
        </footer>
    </div>

    <!-- Client Scripts Composed from Modular Components -->
    <script>
        {get_trip_route_scripts()}
        {get_map_scripts()}
        {get_mpg_scripts()}
        {get_gas_prices_scripts()}
        {get_computation_scripts()}
    </script>
</body>
</html>"""


class UnifiedGasCalculatorHandler(BaseHTTPRequestHandler):
    """Unified HTTP Request Handler that delegates to modular components."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path in ("/", "/index.html"):
            content = build_unified_gas_calculator_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed_url.path == "/api/status":
            has_api_key = bool(get_api_key())
            response_data = {
                "status": "online",
                "app": "gas_calculator",
                "modules_loaded": [
                    "trip_route",
                    "interactive_map",
                    "mpg",
                    "gas_prices",
                    "final_computation"
                ],
                "google_maps_api_configured": has_api_key
            }
            self._send_json(200, response_data)
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._send_json(400, {"success": False, "error": "Empty request body."})
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body)
        except Exception as e:
            self._send_json(400, {"success": False, "error": f"Invalid JSON payload: {str(e)}"})
            return

        if parsed_url.path in ("/api/calculate", "/api/distance"):
            # Delegate calculation directly to modular trip_route backend handler
            result = handle_route_api(payload)
            status_code = 200 if result.get("success") else 400
            self._send_json(status_code, result)

        elif parsed_url.path == "/api/gas-price":
            # Delegate to modular gas_prices backend handler
            zip_or_address = payload.get("zip_code") or payload.get("origin") or ""
            result = get_gas_price_for_zip(zip_or_address)
            status_code = 200 if result.get("success") else 400
            self._send_json(status_code, result)

        elif parsed_url.path in ("/api/final-computation", "/api/compute-trip"):
            # Delegate to modular final_computation backend handler
            result = compute_trip_pipeline(payload)
            status_code = 200 if result.get("success") else 400
            self._send_json(status_code, result)

        else:
            self._send_json(404, {"error": "Endpoint Not Found"})

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_web_server(port: int = 5000, host: str = "127.0.0.1") -> None:
    """Starts the unified HTTP server composed of all modular components."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, UnifiedGasCalculatorHandler)
    print("=" * 65)
    print(" GDG DevFest - Unified Gas Cost Calculator")
    print("=" * 65)
    print(f" Web Application  : http://{host}:{port}/")
    print(f" REST API endpoint : http://{host}:{port}/api/calculate")
    print(" Composed Modules : trip_route + interactive_map + mpg + gas_prices + final_computation")
    print(" Press Ctrl+C to stop the server.")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="GDG DevFest Unified Gas Cost Calculator")
    parser.add_argument("--cli", action="store_true", help="Run in interactive CLI mode instead of web server")
    parser.add_argument("--port", type=int, default=5000, help="Web server port (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    args = parser.parse_args()

    if args.cli:
        run_cli_mode()
    else:
        run_web_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
