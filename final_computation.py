"""
final_computation.py - Modular Final Cost Computation Component for GDG DevFest.
Combines vehicle MPG, regional gas prices, and route distance to compute total trip fuel costs.
Displays the total cost of gas, computed average gas price, and distance traveled
concisely beneath the MPG input box with smooth page scrolling transitions.

Can also be run standalone:
    python "final computation.py"
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional

from mpg import validate_mpg_input
from gas_prices import get_gas_price_for_zip


def calculate_trip_gas_cost(
    distance_miles: float,
    mpg: float,
    gas_price: float,
    origin_location: Optional[str] = None,
    destination_location: Optional[str] = None,
    zip_code: Optional[str] = None,
    gas_source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes fuel consumption and total cost of gas for a trip.
    Formula:
        gallons_needed = distance_miles / mpg
        total_cost = gallons_needed * gas_price
    """
    if distance_miles <= 0:
        return {"success": False, "error": "Trip distance must be greater than 0 miles."}

    if mpg <= 0:
        return {"success": False, "error": "MPG must be greater than 0."}

    if gas_price <= 0:
        return {"success": False, "error": "Gas price must be greater than $0.00."}

    gallons_needed = distance_miles / mpg
    total_cost = gallons_needed * gas_price

    return {
        "success": True,
        "distance_miles": round(distance_miles, 2),
        "mpg": round(mpg, 2),
        "gas_price_per_gallon": round(gas_price, 2),
        "gallons_needed": round(gallons_needed, 2),
        "total_cost": round(total_cost, 2),
        "total_cost_formatted": f"${total_cost:.2f}",
        "currency": "USD",
        "origin": origin_location or "Starting Point",
        "destination": destination_location or "Destination",
        "zip_code": zip_code or "",
        "gas_source": gas_source or "Regional Fuel Index"
    }


def compute_trip_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    End-to-end controller combining distance, MPG, and gas price API lookup.
    """
    try:
        # 1. Parse Distance
        dist_raw = payload.get("distance_miles")
        if dist_raw is None:
            return {"success": False, "error": "Distance is missing from payload."}
        distance_miles = float(dist_raw)
        if distance_miles <= 0:
            return {"success": False, "error": "Distance must be greater than 0 miles."}

        # 2. Parse & Validate MPG from mpg module
        mpg_raw = payload.get("mpg")
        is_valid_mpg, mpg_val, mpg_err = validate_mpg_input(mpg_raw)
        if not is_valid_mpg or mpg_val is None:
            return {"success": False, "error": mpg_err}

        # 3. Retrieve Gas Price for start destination ZIP code
        zip_code = payload.get("zip_code", "")
        origin = payload.get("origin", "")
        lookup_target = zip_code or origin

        gas_data = get_gas_price_for_zip(lookup_target)
        if not gas_data.get("success"):
            return {
                "success": False,
                "error": f"Failed to retrieve gas price: {gas_data.get('error')}"
            }

        avg_price = gas_data.get("average_gas_price", 3.25)
        source_name = gas_data.get("source", "Regional Benchmark")

        # 4. Final Computation
        return calculate_trip_gas_cost(
            distance_miles=distance_miles,
            mpg=mpg_val,
            gas_price=avg_price,
            origin_location=origin,
            destination_location=payload.get("destination", ""),
            zip_code=gas_data.get("zip_code", zip_code),
            gas_source=source_name
        )

    except Exception as e:
        return {"success": False, "error": f"Error during final cost computation: {str(e)}"}


# Modular CSS Styles for Final Computation Display
COMPUTATION_STYLES = """
    .computation-card {
        margin-top: 1.5rem;
        display: none;
        animation: fadeIn 0.4s ease;
        border-color: rgba(66, 133, 244, 0.4);
        background: linear-gradient(180deg, #1E293B 0%, #151F30 100%);
    }

    .computation-hero {
        text-align: center;
        padding: 1.5rem 1rem;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid var(--card-border);
        border-radius: 1rem;
        margin-bottom: 1.5rem;
    }

    .computation-hero-label {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 0.35rem;
    }

    .computation-hero-amount {
        font-size: 3.25rem;
        font-weight: 800;
        color: #34A853;
        line-height: 1.1;
        letter-spacing: -0.02em;
        text-shadow: 0 0 20px rgba(52, 168, 83, 0.25);
    }

    .computation-hero-sub {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: 0.35rem;
    }

    .computation-metrics-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-bottom: 1.25rem;
    }

    @media (max-width: 600px) {
        .computation-metrics-grid {
            grid-template-columns: 1fr;
        }
    }

    .metric-box {
        background: var(--input-bg);
        border: 1px solid var(--card-border);
        border-radius: 0.85rem;
        padding: 1rem;
        text-align: center;
    }

    .metric-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        font-size: 1.35rem;
        font-weight: 800;
        color: #F8FAFC;
    }

    .metric-sub {
        font-size: 0.75rem;
        color: #94A3B8;
        margin-top: 0.25rem;
    }

    .computation-formula-bar {
        background: rgba(66, 133, 244, 0.08);
        border: 1px solid rgba(66, 133, 244, 0.25);
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        font-size: 0.82rem;
        color: #93C5FD;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
"""


def get_computation_html() -> str:
    """Returns the HTML markup for the final computation card component."""
    return """
        <!-- Final Trip Cost Computation Card (Displayed beneath MPG input) -->
        <div id="computation-container-card" class="card computation-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                <div>
                    <span class="badge" style="margin-bottom: 0; background: rgba(52, 168, 83, 0.15); color: #34A853; border-color: rgba(52, 168, 83, 0.3);">
                        Final Computation
                    </span>
                    <h3 style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-top: 0.25rem;">
                        Trip Gas Cost Summary
                    </h3>
                </div>
            </div>

            <!-- Hero Cost Display -->
            <div class="computation-hero">
                <div class="computation-hero-label">Total Estimated Gas Cost</div>
                <div class="computation-hero-amount" id="final-total-cost">$0.00</div>
                <div class="computation-hero-sub" id="final-cost-subtitle">
                    Estimated for round-trip / one-way driving route
                </div>
            </div>

            <!-- Concise Metric Displays -->
            <div class="computation-metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Computed Gas Price</div>
                    <div class="metric-value" id="final-gas-price" style="color: #60A5FA;">$0.00 / gal</div>
                    <div class="metric-sub" id="final-gas-source">Regional Average</div>
                </div>

                <div class="metric-box">
                    <div class="metric-label">Distance Traveled</div>
                    <div class="metric-value" id="final-distance" style="color: #F8FAFC;">0 mi</div>
                    <div class="metric-sub" id="final-fuel-consumed">0.00 gal consumed</div>
                </div>

                <div class="metric-box">
                    <div class="metric-label">Vehicle Efficiency</div>
                    <div class="metric-value" id="final-mpg" style="color: #34A853;">0 MPG</div>
                    <div class="metric-sub">User Defined</div>
                </div>
            </div>

            <!-- Formula Breakdown -->
            <div class="computation-formula-bar">
                <span>
                    <strong>Calculation:</strong>
                    <span id="final-formula-text">(0 mi ÷ 0 MPG) × $0.00/gal = $0.00</span>
                </span>
                <span id="final-zip-tag" style="font-weight: 600; color: #E2E8F0;"></span>
            </div>
        </div>
    """


def get_computation_scripts() -> str:
    """Returns client-side JavaScript for rendering computed results and smooth page scrolling."""
    return """
        function renderFinalComputation(result) {
            const card = document.getElementById('computation-container-card');
            if (!card) return;

            // Populate Total Cost
            document.getElementById('final-total-cost').textContent = result.total_cost_formatted || `$${result.total_cost.toFixed(2)}`;
            document.getElementById('final-cost-subtitle').textContent =
                `Fuel cost for ${result.distance_miles} miles at ${result.mpg} MPG`;

            // Populate Computed Average Gas Price
            document.getElementById('final-gas-price').textContent = `$${result.gas_price_per_gallon.toFixed(2)} / gal`;
            document.getElementById('final-gas-source').textContent = result.gas_source || 'Regional Index';

            // Populate Distance Traveled & Fuel Consumed
            document.getElementById('final-distance').textContent = `${result.distance_miles} mi`;
            document.getElementById('final-fuel-consumed').textContent = `${result.gallons_needed} gal needed`;

            // Populate Vehicle MPG
            document.getElementById('final-mpg').textContent = `${result.mpg} MPG`;

            // Populate Formula breakdown
            const formula = `(${result.distance_miles} mi ÷ ${result.mpg} MPG) × $${result.gas_price_per_gallon.toFixed(2)}/gal = $${result.total_cost.toFixed(2)}`;
            document.getElementById('final-formula-text').textContent = formula;

            if (result.zip_code) {
                document.getElementById('final-zip-tag').textContent = `ZIP: ${result.zip_code}`;
            }

            // Reveal the card
            card.style.display = 'block';

            // Smooth scroll down to reveal the final computation, behaving like the route-to-map transition
            setTimeout(() => {
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 250);
        }
    """


def get_standalone_computation_page() -> str:
    """Builds a standalone preview page for testing final_computation alone."""
    from trip_route import BASE_STYLES

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Final Gas Cost Computation | GDG DevFest</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        {BASE_STYLES}
        {COMPUTATION_STYLES}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="badge">GDG DevFest Hackathon</span>
            <h1>Final Trip Computation</h1>
            <p>Standalone preview of gas cost and fuel consumption calculation</p>
        </header>

        {get_computation_html()}

        <script>
            {get_computation_scripts()}
            document.addEventListener('DOMContentLoaded', () => {{
                renderFinalComputation({{
                    distance_miles: 154.2,
                    mpg: 28.0,
                    gas_price_per_gallon: 3.89,
                    gallons_needed: 5.51,
                    total_cost: 21.43,
                    total_cost_formatted: "$21.43",
                    gas_source: "California Regional Benchmark",
                    zip_code: "90210"
                }});
            }});
        </script>
    </div>
</body>
</html>"""


def main() -> None:
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class StandaloneComputationHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            content = get_standalone_computation_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = HTTPServer(("127.0.0.1", 5004), StandaloneComputationHandler)
    print("=" * 65)
    print(" GDG DevFest - Final Gas Cost Computation Component (Standalone)")
    print(" Running at: http://127.0.0.1:5004/")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    main()
