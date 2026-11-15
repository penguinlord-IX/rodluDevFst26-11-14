"""
gas_calculator.py - Unified Coordinator for the GDG DevFest Gas Cost Calculator.
Imports and orchestrates both trip_route and interactive_map together into a unified app.
Keeps each section modular so they can be expanded independently.

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

# 3. Import shared configuration
from route_service import get_api_key


def build_unified_gas_calculator_page() -> str:
    """
    Composes the unified Web UI by assembling the modular sections together.
    No code duplication: imports HTML and JS directly from trip_route and interactive_map.
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
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Gas Cost Calculator</h1>
            <p>Compute trip route distance, view interactive maps, and calculate road travel</p>
        </header>

        <!-- Section 1: Modular Trip Route & Distance Component -->
        {get_trip_route_html()}

        <!-- Section 2: Modular Interactive Map Component -->
        {get_map_html()}

        <footer class="footer">
            Modular Gas Cost Calculator • GDG DevFest Hackathon
        </footer>
    </div>

    <!-- Client Scripts Composed from Modules -->
    <script>
        {get_trip_route_scripts()}
        {get_map_scripts()}
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
                "modules_loaded": ["trip_route", "interactive_map"],
                "google_maps_api_configured": has_api_key
            }
            self._send_json(200, response_data)
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path in ("/api/calculate", "/api/distance"):
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

            # Delegate calculation directly to modular trip_route backend handler
            result = handle_route_api(payload)

            status_code = 200 if result.get("success") else 400
            self._send_json(status_code, result)
        else:
            self._send_json(404, {"error": "Not Found"})

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_web_server(port: int = 5000, host: str = "127.0.0.1") -> None:
    """Starts the unified HTTP server composed of both modular components."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, UnifiedGasCalculatorHandler)
    print("=" * 65)
    print(" GDG DevFest - Unified Gas Cost Calculator")
    print("=" * 65)
    print(f" Web Application  : http://{host}:{port}/")
    print(f" REST API endpoint : http://{host}:{port}/api/calculate")
    print(" Composed Modules : trip_route + interactive_map")
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
