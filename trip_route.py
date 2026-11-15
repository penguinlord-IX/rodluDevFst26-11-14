"""
trip_route.py - Modular Trip Route and Distance Component for GDG DevFest.
Exports modular UI and client scripts so orchestrator apps (like gas_calculator.py)
can import and compose this section cleanly without duplicating code.

Can also be run standalone:
    python "trip route.py"
    python trip_route.py --cli
"""

import sys
import json
import argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from route_service import (
    calculate_distance,
    get_google_maps_distance,
    validate_manual_miles,
    get_api_key
)

# Shared Base CSS Design System
BASE_STYLES = """
    :root {
        --primary: #4285F4;
        --primary-hover: #3367D6;
        --secondary: #34A853;
        --warning: #FBBC05;
        --danger: #EA4335;
        --bg: #0F172A;
        --card-bg: #1E293B;
        --card-border: #334155;
        --text-main: #F8FAFC;
        --text-muted: #94A3B8;
        --input-bg: #0F172A;
        --input-border: #475569;
        --focus-ring: rgba(66, 133, 244, 0.4);
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    body {
        background: var(--bg);
        color: var(--text-main);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 2.5rem 1rem;
    }

    .container {
        width: 100%;
        max-width: 760px;
    }

    .header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .header .badge {
        display: inline-block;
        background: rgba(66, 133, 244, 0.15);
        color: var(--primary);
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(66, 133, 244, 0.3);
    }

    .header h1 {
        font-size: 2.25rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #FFFFFF 0%, #CBD5E1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .header p {
        color: var(--text-muted);
        font-size: 0.95rem;
    }

    .card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 1.25rem;
        padding: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
        margin-bottom: 1.5rem;
    }

    .tab-nav {
        display: flex;
        background: var(--input-bg);
        padding: 0.35rem;
        border-radius: 0.85rem;
        border: 1px solid var(--card-border);
        margin-bottom: 1.75rem;
        gap: 0.35rem;
    }

    .tab-btn {
        flex: 1;
        padding: 0.75rem 1rem;
        border: none;
        border-radius: 0.6rem;
        background: transparent;
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .tab-btn.active {
        background: var(--primary);
        color: #FFFFFF;
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.35);
    }

    .form-group {
        margin-bottom: 1.25rem;
    }

    .form-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.45rem;
        color: #E2E8F0;
    }

    .form-label span.req {
        color: var(--danger);
        margin-left: 0.25rem;
    }

    .form-label span.hint {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 400;
    }

    .form-input {
        width: 100%;
        background: var(--input-bg);
        border: 1px solid var(--input-border);
        border-radius: 0.75rem;
        padding: 0.85rem 1rem;
        font-size: 0.95rem;
        color: var(--text-main);
        outline: none;
        transition: all 0.2s ease;
    }

    .form-input:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px var(--focus-ring);
    }

    .form-input::placeholder {
        color: #64748B;
    }

    .info-box {
        background: rgba(66, 133, 244, 0.08);
        border: 1px solid rgba(66, 133, 244, 0.25);
        border-radius: 0.75rem;
        padding: 0.85rem 1rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        font-size: 0.825rem;
        color: #93C5FD;
        line-height: 1.4;
    }

    .info-box svg {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        margin-top: 1px;
    }

    .btn-submit {
        width: 100%;
        background: var(--primary);
        color: #FFFFFF;
        border: none;
        border-radius: 0.75rem;
        padding: 0.95rem 1.5rem;
        font-size: 1rem;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        box-shadow: 0 4px 14px rgba(66, 133, 244, 0.35);
    }

    .btn-submit:hover:not(:disabled) {
        background: var(--primary-hover);
        transform: translateY(-1px);
    }

    .btn-submit:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
    }

    .spinner {
        display: none;
        width: 18px;
        height: 18px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: #FFFFFF;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .result-container {
        display: none;
        margin-top: 1.5rem;
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .alert-error {
        background: rgba(234, 67, 53, 0.12);
        border: 1px solid rgba(234, 67, 53, 0.4);
        color: #FCA5A5;
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        font-size: 0.9rem;
        line-height: 1.45;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }

    .alert-error svg {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        margin-top: 2px;
        fill: #EF4444;
    }

    .result-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #334155;
        border-radius: 1rem;
        padding: 1.5rem;
    }

    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
    }

    .result-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: var(--secondary);
    }

    .result-stat {
        text-align: right;
    }

    .stat-miles {
        font-size: 2.25rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1;
    }

    .stat-unit {
        font-size: 1rem;
        color: var(--text-muted);
        margin-left: 0.25rem;
        font-weight: 500;
    }

    .stat-duration {
        font-size: 0.85rem;
        color: #CBD5E1;
        margin-top: 0.35rem;
    }

    .route-details {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .route-point {
        display: flex;
        gap: 0.85rem;
        align-items: flex-start;
    }

    .point-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }

    .point-dot.start { background: var(--primary); box-shadow: 0 0 8px var(--primary); }
    .point-dot.end { background: var(--secondary); box-shadow: 0 0 8px var(--secondary); }
    .point-dot.manual { background: var(--warning); box-shadow: 0 0 8px var(--warning); }

    .point-info h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }

    .point-info p {
        font-size: 0.925rem;
        color: #F1F5F9;
    }

    .next-steps-badge {
        margin-top: 1.25rem;
        padding: 0.75rem 1rem;
        background: rgba(52, 168, 83, 0.1);
        border: 1px dashed rgba(52, 168, 83, 0.35);
        border-radius: 0.75rem;
        font-size: 0.8rem;
        color: #86EFAC;
        text-align: center;
    }

    .footer {
        text-align: center;
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 1.5rem;
    }
"""


def get_trip_route_html() -> str:
    """Returns the HTML markup for the Trip Route & Distance section."""
    return """
        <!-- Trip Route & Distance Card -->
        <div class="card">
            <!-- Mode Toggle Tabs -->
            <div class="tab-nav">
                <button type="button" class="tab-btn active" id="tab-address" onclick="setMode('address')">
                    Google Maps Route
                </button>
                <button type="button" class="tab-btn" id="tab-manual" onclick="setMode('manual')">
                    Specify Number of Miles
                </button>
            </div>

            <!-- Form -->
            <form id="distance-form" onsubmit="handleCalculate(event)">
                <!-- ADDRESS MODE FIELDS -->
                <div id="address-section">
                    <div class="info-box">
                        <svg viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                        <div>
                            <strong>Location & ZIP Code Verification:</strong> Please include a valid 5-digit ZIP code in both addresses and ensure the city/street matches the ZIP code (e.g., <em>Santa Cruz, CA 95060</em> or <em>Alhambra, CA 91803</em>). Mismatched addresses will be flagged as invalid.
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label" for="origin-input">
                            <span>Start Address <span class="req">*</span></span>
                            <span class="hint">Include 5-digit ZIP</span>
                        </label>
                        <input 
                            type="text" 
                            id="origin-input" 
                            class="form-input" 
                            placeholder="e.g. 1600 Amphitheatre Pkwy, Mountain View, CA 94043"
                            autocomplete="street-address"
                        />
                    </div>

                    <div class="form-group">
                        <label class="form-label" for="destination-input">
                            <span>Destination Address <span class="req">*</span></span>
                            <span class="hint">Include 5-digit ZIP</span>
                        </label>
                        <input 
                            type="text" 
                            id="destination-input" 
                            class="form-input" 
                            placeholder="e.g. 1 Infinite Loop, Cupertino, CA 95014"
                            autocomplete="street-address"
                        />
                    </div>
                </div>

                <!-- MANUAL MILES FIELD -->
                <div id="manual-section" style="display: none;">
                    <div class="info-box" style="background: rgba(251, 188, 5, 0.08); border-color: rgba(251, 188, 5, 0.25); color: #FDE68A;">
                        <svg viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                        <div>
                            <strong>Manual Mileage Entry:</strong> Type your estimated or known trip distance in miles directly below.
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label" for="miles-input">
                            <span>Specified Number of Miles <span class="req">*</span></span>
                            <span class="hint">Type numerical distance</span>
                        </label>
                        <input 
                            type="number" 
                            step="any" 
                            min="0.1" 
                            id="miles-input" 
                            class="form-input" 
                            placeholder="Type distance here (e.g., 42.5)"
                        />
                    </div>
                </div>

                <!-- Submit Button -->
                <button type="submit" id="submit-btn" class="btn-submit">
                    <span class="spinner" id="btn-spinner"></span>
                    <span id="btn-text">Calculate Trip Distance</span>
                </button>
            </form>

            <!-- Results & Error Area -->
            <div id="result-area" class="result-container"></div>
        </div>
    """


def get_trip_route_scripts() -> str:
    """Returns the JavaScript logic for trip route calculations and inputs."""
    return """
        let currentMode = 'address';

        function setMode(mode) {
            currentMode = mode;
            const tabAddress = document.getElementById('tab-address');
            const tabManual = document.getElementById('tab-manual');
            const addressSec = document.getElementById('address-section');
            const manualSec = document.getElementById('manual-section');
            const resultArea = document.getElementById('result-area');
            const mapCard = document.getElementById('map-container-card');

            resultArea.style.display = 'none';
            if (mapCard) mapCard.style.display = 'none';

            if (mode === 'address') {
                tabAddress.classList.add('active');
                tabManual.classList.remove('active');
                addressSec.style.display = 'block';
                manualSec.style.display = 'none';
                document.getElementById('btn-text').textContent = 'Calculate Google Maps Route';
            } else {
                tabManual.classList.add('active');
                tabAddress.classList.remove('active');
                addressSec.style.display = 'none';
                manualSec.style.display = 'block';
                document.getElementById('btn-text').textContent = 'Confirm Specified Miles';
            }
        }

        async function handleCalculate(event) {
            event.preventDefault();

            const resultArea = document.getElementById('result-area');
            const submitBtn = document.getElementById('submit-btn');
            const spinner = document.getElementById('btn-spinner');
            const btnText = document.getElementById('btn-text');

            resultArea.style.display = 'none';
            resultArea.innerHTML = '';

            let payload = { mode: currentMode };

            if (currentMode === 'address') {
                const origin = document.getElementById('origin-input').value.trim();
                const destination = document.getElementById('destination-input').value.trim();

                if (!origin) {
                    showError("Please enter a starting address.");
                    return;
                }
                if (!destination) {
                    showError("Please enter a destination address.");
                    return;
                }

                const zipRegex = /\\b\\d{5}(?:-\\d{4})?\\b/;
                if (!zipRegex.test(origin)) {
                    showError("Start address must include a valid 5-digit ZIP code (e.g., '123 Main St, Springfield, IL 62701').");
                    return;
                }
                if (!zipRegex.test(destination)) {
                    showError("Destination address must include a valid 5-digit ZIP code (e.g., '456 Market St, San Francisco, CA 94105').");
                    return;
                }

                payload.origin = origin;
                payload.destination = destination;
            } else {
                const milesRaw = document.getElementById('miles-input').value.trim();
                if (!milesRaw) {
                    showError("Please type the specified number of miles.");
                    return;
                }
                const num = parseFloat(milesRaw);
                if (isNaN(num) || num <= 0) {
                    showError("Please type a valid positive number for miles.");
                    return;
                }
                payload.manual_miles = milesRaw;
            }

            submitBtn.disabled = true;
            spinner.style.display = 'inline-block';
            const originalBtnText = btnText.textContent;
            btnText.textContent = 'Calculating...';

            try {
                const response = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (!data.success) {
                    showError(data.error || "Failed to calculate distance.");
                } else {
                    showSuccess(data);
                }
            } catch (err) {
                showError("Network or server connection error: " + err.message);
            } finally {
                submitBtn.disabled = false;
                spinner.style.display = 'none';
                btnText.textContent = originalBtnText;
            }
        }

        function showError(msg) {
            const resultArea = document.getElementById('result-area');
            const mapCard = document.getElementById('map-container-card');
            if (mapCard) mapCard.style.display = 'none';

            resultArea.innerHTML = `
                <div class="alert-error">
                    <svg viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                    <div>${msg}</div>
                </div>
            `;
            resultArea.style.display = 'block';
        }

        function showSuccess(data) {
            const resultArea = document.getElementById('result-area');
            const isManual = data.mode === 'manual';

            let routeDetailsHtml = '';
            if (!isManual) {
                routeDetailsHtml = `
                    <div class="route-details">
                        <div class="route-point">
                            <span class="point-dot start"></span>
                            <div class="point-info">
                                <h4>Start Location (Validated)</h4>
                                <p>${escapeHtml(data.origin_formatted || data.origin_input)}</p>
                            </div>
                        </div>
                        <div class="route-point">
                            <span class="point-dot end"></span>
                            <div class="point-info">
                                <h4>Destination (Validated)</h4>
                                <p>${escapeHtml(data.destination_formatted || data.destination_input)}</p>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                routeDetailsHtml = `
                    <div class="route-details">
                        <div class="route-point">
                            <span class="point-dot manual"></span>
                            <div class="point-info">
                                <h4>Trip Type</h4>
                                <p>Custom Specified Distance (Typed Input)</p>
                            </div>
                        </div>
                    </div>
                `;
            }

            resultArea.innerHTML = `
                <div class="result-card">
                    <div class="result-header">
                        <span class="result-title">Trip Route Distance</span>
                        <div class="result-stat">
                            <div class="stat-miles">${data.distance_miles}<span class="stat-unit">mi</span></div>
                            <div class="stat-duration">${escapeHtml(data.duration_text || '')}</div>
                        </div>
                    </div>
                    ${routeDetailsHtml}
                    <div class="next-steps-badge">
                        Ready for Next Step: Gas Price Regional Lookup & Carpool Cost Split
                    </div>
                </div>
            `;
            resultArea.style.display = 'block';

            // Decoupled notification: If interactive map component is loaded, update it
            if (typeof initOrUpdateMap === 'function') {
                initOrUpdateMap(data);
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    """


def handle_route_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Backend controller function for distance calculation requests."""
    mode = payload.get("mode", "address")
    origin = payload.get("origin", "")
    destination = payload.get("destination", "")
    manual_miles = payload.get("manual_miles")

    return calculate_distance(
        mode=mode,
        origin=origin,
        destination=destination,
        manual_miles=manual_miles
    )


def get_standalone_trip_route_page() -> str:
    """Builds the standalone HTML page for testing trip_route independently."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trip Route & Distance Calculator | GDG DevFest</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        {BASE_STYLES}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Trip Route & Distance</h1>
            <p>Compute driving distance between locations or specify custom trip mileage</p>
        </header>

        {get_trip_route_html()}

        <footer class="footer">
            Modular Gas Cost Calculator • Trip Route Module • GDG DevFest Hackathon
        </footer>
    </div>

    <script>
        {get_trip_route_scripts()}
    </script>
</body>
</html>"""


class TripRouteRequestHandler(BaseHTTPRequestHandler):
    """Standalone HTTP Request Handler for trip_route."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path in ("/", "/index.html"):
            content = get_standalone_trip_route_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed_url.path == "/api/status":
            res = {"status": "online", "module": "trip_route", "google_maps_api_configured": bool(get_api_key())}
            self._send_json(200, res)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path in ("/api/calculate", "/api/distance"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if body else {}
            result = handle_route_api(payload)
            self._send_json(200 if result.get("success") else 400, result)
        else:
            self.send_error(404)

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_cli_mode() -> None:
    """Interactive command-line interface for the Trip Route module."""
    print("=" * 60)
    print(" GDG DevFest - Trip Route & Distance Calculator (CLI Mode)")
    print("=" * 60)
    print("Select trip distance input method:")
    print("  1. Google Maps Route (Origin & Destination addresses)")
    print("  2. Specify Number of Miles (Manual typed input)")
    print("=" * 60)

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        print("\nNote: Addresses must include a 5-digit ZIP code for accurate routing.")
        origin = input("Enter Start Address: ").strip()
        dest = input("Enter Destination Address: ").strip()

        print("\nCalculating route via Google Routes API...")
        res = handle_route_api({"mode": "address", "origin": origin, "destination": dest})

        if res.get("success"):
            print("\n" + "=" * 40)
            print(" TRIP ROUTE COMPUTED SUCCESSFULLY")
            print("=" * 40)
            print(f" Start Location : {res.get('origin_formatted')}")
            print(f" Destination    : {res.get('destination_formatted')}")
            print(f" Driving Distance: {res.get('distance_miles')} miles ({res.get('distance_text')})")
            print(f" Travel Time     : {res.get('duration_text')}")
            print("=" * 40)
        else:
            print("\n[ERROR]", res.get("error"))

    elif choice == "2":
        miles_input = input("\nType the specified number of miles: ").strip()
        res = handle_route_api({"mode": "manual", "manual_miles": miles_input})

        if res.get("success"):
            print("\n" + "=" * 40)
            print(" SPECIFIED MILES RECORDED")
            print("=" * 40)
            print(f" Distance: {res.get('distance_miles')} miles")
            print("=" * 40)
        else:
            print("\n[ERROR]", res.get("error"))
    else:
        print("Invalid option. Please run again and select 1 or 2.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trip Route and Distance Calculator")
    parser.add_argument("--cli", action="store_true", help="Run in interactive CLI mode instead of web server")
    parser.add_argument("--port", type=int, default=5000, help="Web server port (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    args = parser.parse_args()

    if args.cli:
        run_cli_mode()
    else:
        server_address = (args.host, args.port)
        httpd = HTTPServer(server_address, TripRouteRequestHandler)
        print("=" * 60)
        print(" GDG DevFest - Trip Route & Distance Calculator")
        print(f" Running at: http://{args.host}:{args.port}/")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping...")
            httpd.server_close()


if __name__ == "__main__":
    main()
