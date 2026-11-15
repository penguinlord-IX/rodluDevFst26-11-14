"""
mpg.py - Modular Vehicle Fuel Economy (MPG) Component for GDG DevFest Hackathon.
Allows user to input the MPG of their car via text box input underneath the map display,
with smooth page scrolling transitions between sections.

Can also be run standalone:
    python "mpg.py"
"""

import sys
import json
import argparse
from typing import Dict, Any, Tuple, Optional


def validate_mpg_input(mpg_raw: Any) -> Tuple[bool, Optional[float], str]:
    """
    Validates user-inputted Miles Per Gallon (MPG).
    Returns (is_valid, mpg_float, error_message).
    """
    if mpg_raw is None:
        return False, None, "MPG is required. Please enter the MPG of your vehicle."

    if isinstance(mpg_raw, str):
        cleaned = mpg_raw.strip()
        if not cleaned:
            return False, None, "MPG field cannot be empty. Please enter your car's MPG."
        try:
            val = float(cleaned)
        except ValueError:
            return False, None, f"Invalid MPG value '{cleaned}'. Please type a valid number (e.g., 28 or 32.5)."
    elif isinstance(mpg_raw, (int, float)):
        val = float(mpg_raw)
    else:
        return False, None, "Invalid MPG format. Please type a number."

    if val <= 0:
        return False, None, "MPG must be a positive number greater than 0."

    if val > 150:
        return False, None, "MPG exceeds typical vehicle range (maximum 150 MPG). Please check your input."

    return True, round(val, 2), ""


# Modular CSS Styles for the MPG Component
MPG_STYLES = """
    .mpg-card {
        margin-top: 1.5rem;
        display: none;
        animation: fadeIn 0.4s ease;
    }

    .mpg-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .mpg-title-group h3 {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 0.25rem;
    }

    .mpg-input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
    }

    .mpg-unit-label {
        position: absolute;
        right: 1rem;
        color: var(--text-muted);
        font-weight: 700;
        font-size: 0.9rem;
        pointer-events: none;
    }

    .mpg-presets {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
        margin-bottom: 1.25rem;
    }

    .btn-preset {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--card-border);
        color: var(--text-muted);
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-preset:hover {
        background: rgba(66, 133, 244, 0.15);
        border-color: var(--primary);
        color: #FFFFFF;
    }

    .mpg-actions {
        display: flex;
        gap: 0.75rem;
        align-items: center;
    }
"""


def get_mpg_html() -> str:
    """Returns the HTML markup for the MPG input card component."""
    return """
        <!-- Vehicle MPG Input Card (Displayed underneath Interactive Map) -->
        <div id="mpg-container-card" class="card mpg-card">
            <div class="mpg-header">
                <div class="mpg-title-group">
                    <span class="badge" style="margin-bottom: 0;">Vehicle Efficiency</span>
                    <h3>Input Car Fuel Economy (MPG)</h3>
                </div>
            </div>

            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.25rem;">
                Enter your vehicle's average Miles Per Gallon (MPG) to calculate the fuel consumption and estimated gas cost for this route.
            </p>

            <form id="mpg-form" onsubmit="event.preventDefault(); submitMpg();">
                <div class="form-group">
                    <label class="form-label" for="car-mpg-input">
                        Miles Per Gallon (MPG) <span class="req">*</span>
                    </label>
                    <div class="mpg-input-wrapper">
                        <input
                            type="number"
                            id="car-mpg-input"
                            class="form-input"
                            placeholder="e.g., 28.5"
                            min="1"
                            max="150"
                            step="0.1"
                            required
                        />
                        <span class="mpg-unit-label">MPG</span>
                    </div>
                </div>

                <!-- Quick Presets -->
                <div class="mpg-presets">
                    <span style="font-size: 0.78rem; color: var(--text-muted); display: flex; align-items: center; margin-right: 0.25rem;">
                        Quick Presets:
                    </span>
                    <button type="button" class="btn-preset" onclick="setMpgValue(30)">🚗 Sedan (30 MPG)</button>
                    <button type="button" class="btn-preset" onclick="setMpgValue(24)">🚙 SUV (24 MPG)</button>
                    <button type="button" class="btn-preset" onclick="setMpgValue(18)">🛻 Truck (18 MPG)</button>
                    <button type="button" class="btn-preset" onclick="setMpgValue(50)">⚡ Hybrid (50 MPG)</button>
                </div>

                <div class="mpg-actions">
                    <button type="submit" id="btn-submit-mpg" class="btn btn-primary" style="width: 100%;">
                        <span class="spinner" id="mpg-spinner" style="display: none;"></span>
                        <span id="mpg-btn-text">Compute Trip Gas Cost</span>
                    </button>
                </div>
            </form>

            <!-- Inline Error Display for MPG Input -->
            <div id="mpg-error-area" style="display: none; margin-top: 1rem;"></div>
        </div>
    """


def get_mpg_scripts() -> str:
    """Returns client-side JavaScript for handling MPG input, validation, and smooth scrolling."""
    return """
        // Cached trip state shared with other modules
        let currentTripData = null;

        function setMpgValue(val) {
            const input = document.getElementById('car-mpg-input');
            if (input) {
                input.value = val;
                input.focus();
            }
        }

        function promptMpgSection(routeData) {
            currentTripData = routeData;
            const mpgCard = document.getElementById('mpg-container-card');
            if (!mpgCard) return;

            // Reveal MPG section beneath the map
            mpgCard.style.display = 'block';

            // Clear any prior errors
            const errArea = document.getElementById('mpg-error-area');
            if (errArea) {
                errArea.innerHTML = '';
                errArea.style.display = 'none';
            }

            // Smooth scroll down to prompt MPG input, behaving like the map transition
            setTimeout(() => {
                mpgCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                const mpgInput = document.getElementById('car-mpg-input');
                if (mpgInput) mpgInput.focus();
            }, 350);
        }

        async function submitMpg() {
            const mpgInput = document.getElementById('car-mpg-input');
            const submitBtn = document.getElementById('btn-submit-mpg');
            const spinner = document.getElementById('mpg-spinner');
            const btnText = document.getElementById('mpg-btn-text');
            const errArea = document.getElementById('mpg-error-area');

            if (errArea) {
                errArea.innerHTML = '';
                errArea.style.display = 'none';
            }

            const rawVal = mpgInput ? mpgInput.value.trim() : '';
            if (!rawVal) {
                showMpgError("Please enter your vehicle's MPG.");
                return;
            }

            const mpgVal = parseFloat(rawVal);
            if (isNaN(mpgVal) || mpgVal <= 0) {
                showMpgError("Please enter a valid positive number for MPG.");
                return;
            }

            if (mpgVal > 150) {
                showMpgError("MPG exceeds typical vehicle range (maximum 150 MPG).");
                return;
            }

            if (!currentTripData || !currentTripData.distance_miles) {
                showMpgError("Trip route distance is missing. Please calculate your route first.");
                return;
            }

            // Enter loading state
            submitBtn.disabled = true;
            spinner.style.display = 'inline-block';
            const originalText = btnText.textContent;
            btnText.textContent = 'Calculating Gas Cost...';

            try {
                // Determine start destination ZIP code or location
                let originLocation = currentTripData.origin_formatted || currentTripData.origin_input || '';
                let zipCode = '';

                // Extract 5-digit zip code from origin if available
                const zipMatch = originLocation.match(/\\b\\d{5}(?:-\\d{4})?\\b/);
                if (zipMatch) {
                    zipCode = zipMatch[0].substring(0, 5);
                }

                // Call modular unified backend computation API
                const response = await fetch('/api/final-computation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        distance_miles: currentTripData.distance_miles,
                        mpg: mpgVal,
                        zip_code: zipCode,
                        origin: originLocation,
                        destination: currentTripData.destination_formatted || currentTripData.destination_input || ''
                    })
                });

                const result = await response.json();

                if (!result.success) {
                    showMpgError(result.error || "Failed to calculate gas cost.");
                } else {
                    // Forward computed results to Final Computation display module
                    if (typeof renderFinalComputation === 'function') {
                        renderFinalComputation(result);
                    }
                }
            } catch (err) {
                showMpgError("Network or server connection error: " + err.message);
            } finally {
                submitBtn.disabled = false;
                spinner.style.display = 'none';
                btnText.textContent = originalText;
            }
        }

        function showMpgError(msg) {
            const errArea = document.getElementById('mpg-error-area');
            if (errArea) {
                errArea.innerHTML = `
                    <div class="alert-error">
                        <svg viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <div>${msg}</div>
                    </div>
                `;
                errArea.style.display = 'block';
            }
        }
    """


def get_standalone_mpg_page() -> str:
    """Builds standalone page for testing mpg.py independently."""
    from trip_route import BASE_STYLES

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vehicle Fuel Economy (MPG) | GDG DevFest</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        {BASE_STYLES}
        {MPG_STYLES}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Vehicle MPG Input</h1>
            <p>Standalone preview of vehicle fuel efficiency component</p>
        </header>

        {get_mpg_html()}

        <script>
            {get_mpg_scripts()}
            // Initialize standalone demo state
            document.addEventListener('DOMContentLoaded', () => {{
                promptMpgSection({{
                    distance_miles: 120.5,
                    origin_formatted: "Los Angeles, CA 90001",
                    destination_formatted: "San Diego, CA 92101"
                }});
            }});
        </script>
    </div>
</body>
</html>"""


def main() -> None:
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class StandaloneMpgHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            content = get_standalone_mpg_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = HTTPServer(("127.0.0.1", 5003), StandaloneMpgHandler)
    print("=" * 60)
    print(" GDG DevFest - Vehicle MPG Component (Standalone)")
    print(" Running at: http://127.0.0.1:5003/")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    main()
