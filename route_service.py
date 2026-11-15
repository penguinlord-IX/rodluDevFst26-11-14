"""
route_service.py - Backend service for route and distance calculation.
Handles Google Maps API integration, ZIP code validation, address existence checks,
and manual mileage input validation.
"""

import os
import re
import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional


def load_env_file(filepath: Optional[str] = None) -> None:
    """
    Safely loads environment variables from a .env file without external dependencies.
    Resolves relative to this file's directory and handles UTF-8 with or without BOM.
    """
    if filepath is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, ".env")

    if not os.path.exists(filepath):
        return

    try:
        # Use utf-8-sig to automatically strip any Windows UTF-8 BOM (\ufeff)
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip().lstrip("\ufeff")
                val = val.strip().strip("'\"")
                if key:
                    os.environ[key] = val
    except Exception:
        pass


# Load .env variables on import
load_env_file()


def get_api_key() -> Optional[str]:
    """Retrieve Google Maps API Key from environment variables, reloading if unset."""
    key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        load_env_file()
        key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return key.strip() if key else None


def extract_zip_code(address: str) -> Optional[str]:
    """
    Extracts a 5-digit US ZIP code (or 5+4 format) from an address string.
    Returns the ZIP string if found, otherwise None.
    """
    if not address or not isinstance(address, str):
        return None
    # Matches 5 digits, optionally followed by a hyphen and 4 digits (e.g., 90210 or 90210-1234)
    match = re.search(r"\b\d{5}(?:-\d{4})?\b", address.strip())
    return match.group(0) if match else None


def validate_address_has_zip(address: str, field_name: str = "Address") -> Tuple[bool, str]:
    """
    Validates that an address includes a ZIP code for accurate location resolution.
    Returns (is_valid, error_message).
    """
    if not address or not address.strip():
        return False, f"{field_name} cannot be empty."

    zip_code = extract_zip_code(address)
    if not zip_code:
        return (
            False,
            f"{field_name} must include a valid 5-digit ZIP code (e.g., '123 Main St, Springfield, IL 62701') "
            f"to ensure accurate location mapping."
        )
    return True, ""


def extract_city_candidates(addr_str: str, user_zip: str, state_short: str = "", state_long: str = "") -> list:
    """
    Extracts potential city or location words from the user's input by removing
    street numbers, street suffixes, state abbreviations, and the ZIP code.
    """
    cleaned = addr_str
    if user_zip:
        cleaned = re.sub(r"\b" + re.escape(user_zip) + r"(?:-\d{4})?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{5}(?:-\d{4})?\b", "", cleaned)
    if state_short:
        cleaned = re.sub(r"\b" + re.escape(state_short) + r"\b", "", cleaned, flags=re.IGNORECASE)
    if state_long:
        cleaned = re.sub(r"\b" + re.escape(state_long) + r"\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(USA|United States|US)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\b", "", cleaned)

    street_suffixes = [
        "street", "st", "avenue", "ave", "boulevard", "blvd", "road", "rd",
        "drive", "dr", "lane", "ln", "way", "court", "ct", "circle", "cir",
        "highway", "hwy", "parkway", "pkwy", "place", "pl", "terrace", "ter",
        "suite", "ste", "apt", "apartment", "unit"
    ]
    for sfx in street_suffixes:
        cleaned = re.sub(r"\b" + sfx + r"\b\.?", "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[,\.\#\-\/]", " ", cleaned)
    return [w.strip() for w in cleaned.split() if len(w.strip()) > 1]


def check_address_exists(address: str, api_key: str) -> Dict[str, Any]:
    """
    Uses Google Maps Geocoding API to verify that an address actually exists AND
    strictly validates that the inputted ZIP code corresponds with the city/street.
    Accounts for nonexistent addresses, mismatched ZIP codes (e.g., 'Santa Cruz 91803'
    where 91803 belongs to Alhambra), and ambiguous partial matches.
    """
    encoded_addr = urllib.parse.quote(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GDG-DevFest-GasCalculator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        status = payload.get("status")

        if status == "OK" and payload.get("results"):
            top_result = payload["results"][0]
            formatted_address = top_result.get("formatted_address", address)
            location = top_result.get("geometry", {}).get("location", {})
            partial_match = top_result.get("partial_match", False)

            # 1. Parse address components from Google result
            components = top_result.get("address_components", [])
            res_postal_code = None
            res_locality = None
            res_sublocalities = []
            res_neighborhoods = []
            res_state_short = None
            res_state_long = None
            res_county = None

            for comp in components:
                types = comp.get("types", [])
                if "postal_code" in types:
                    res_postal_code = comp.get("short_name", "")
                if "locality" in types:
                    res_locality = comp.get("long_name", "")
                if "sublocality" in types or "sublocality_level_1" in types or "postal_town" in types:
                    res_sublocalities.append(comp.get("long_name", ""))
                if "neighborhood" in types:
                    res_neighborhoods.append(comp.get("long_name", ""))
                if "administrative_area_level_1" in types:
                    res_state_short = comp.get("short_name", "")
                    res_state_long = comp.get("long_name", "")
                if "administrative_area_level_2" in types:
                    res_county = comp.get("long_name", "")

            postcode_localities = top_result.get("postcode_localities", [])
            user_zip = extract_zip_code(address) or ""

            # 2. Strict Check: Does the resolved postal code match what the user typed?
            if res_postal_code and user_zip:
                if user_zip[:5] != res_postal_code[:5]:
                    return {
                        "exists": False,
                        "error": (
                            f"Invalid address: You entered ZIP code '{user_zip}', but the address resolved to "
                            f"'{formatted_address}' (ZIP {res_postal_code}). "
                            f"The ZIP code does not correspond to this location."
                        )
                    }

            # 3. Strict Check: Does the city/street match the ZIP code's true locality?
            # Build all acceptable location names for this ZIP code
            acceptable_names = set()
            if res_locality:
                acceptable_names.add(res_locality.lower())
            for sub in res_sublocalities:
                acceptable_names.add(sub.lower())
            for neigh in res_neighborhoods:
                acceptable_names.add(neigh.lower())
            for pl in postcode_localities:
                acceptable_names.add(pl.lower())
            if res_county:
                acceptable_names.add(res_county.lower())
                acceptable_names.add(res_county.lower().replace(" county", "").strip())

            user_addr_lower = address.lower()
            has_matching_locality = any(name in user_addr_lower for name in acceptable_names if len(name) >= 3)

            # Check if user typed a conflicting city name (e.g. 'Santa Cruz' when ZIP is 91803 Alhambra)
            city_words = extract_city_candidates(address, user_zip, res_state_short or "", res_state_long or "")

            if not has_matching_locality:
                state_display = f", {res_state_short}" if res_state_short else ""
                true_city = res_locality or (res_sublocalities[0] if res_sublocalities else "another city")

                if city_words:
                    candidate_text = " ".join(city_words)
                    # If candidate does not match any valid name for this ZIP code
                    if not any(candidate_text.lower() == n for n in acceptable_names):
                        return {
                            "exists": False,
                            "error": (
                                f"Invalid address: ZIP code {user_zip} belongs to {true_city}{state_display}, "
                                f"which does not correspond to '{candidate_text}'. "
                                f"Please enter a valid address where the street/city matches the ZIP code."
                            )
                        }

                # If Google flagged partial_match because the city/street didn't match the ZIP code
                if partial_match:
                    return {
                        "exists": False,
                        "error": (
                            f"Invalid address: ZIP code {user_zip} belongs to {true_city}{state_display}, "
                            f"which does not correspond to your entered address. "
                            f"Please verify your street, city, and ZIP code."
                        )
                    }

            return {
                "exists": True,
                "formatted_address": formatted_address,
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "locality": res_locality,
                "postal_code": res_postal_code,
                "error": None
            }
        elif status == "ZERO_RESULTS":
            return {
                "exists": False,
                "error": f"Address not found: '{address}' does not exist or could not be located. "
                         f"Please verify the street, city, state, and ZIP code."
            }
        elif status == "REQUEST_DENIED":
            err_msg = payload.get("error_message", "API key is invalid or Geocoding API is not enabled.")
            return {"exists": False, "error": f"Google Maps API Request Denied: {err_msg}"}
        elif status == "OVER_QUERY_LIMIT":
            return {"exists": False, "error": "Google Maps API quota exceeded. Please try again later."}
        else:
            return {
                "exists": False,
                "error": f"Google Maps Geocoding error ({status}): {payload.get('error_message', 'Unknown error')}"
            }

    except urllib.error.URLError as e:
        return {"exists": False, "error": f"Network error contacting Google Maps API: {str(e)}"}
    except json.JSONDecodeError:
        return {"exists": False, "error": "Failed to parse Google Maps API response."}
    except Exception as e:
        return {"exists": False, "error": f"Unexpected error checking address: {str(e)}"}


def format_duration(seconds: int) -> str:
    """Formats a duration in seconds into a human-readable string."""
    if seconds <= 0:
        return "N/A"
    if seconds < 60:
        return f"{seconds} secs"
    total_minutes = seconds // 60
    if total_minutes < 60:
        return f"{total_minutes} mins"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if mins == 0:
        return f"{hours} hr{'s' if hours > 1 else ''}"
    return f"{hours} hr{'s' if hours > 1 else ''} {mins} min{'s' if mins != 1 else ''}"


def get_routes_api_distance(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    key: str
) -> Dict[str, Any]:
    """
    Calls the modern Google Routes API (computeRoutes) for driving distance and duration.
    This is the modern replacement for the legacy Distance Matrix API.
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline",
        "User-Agent": "GDG-DevFest-GasCalculator/1.0"
    }
    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_lat,
                    "longitude": origin_lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dest_lat,
                    "longitude": dest_lng
                }
            }
        },
        "travelMode": "DRIVE"
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        routes = data.get("routes", [])
        if not routes:
            return {"success": False, "error": "No road route found between locations."}

        route = routes[0]
        distance_meters = route.get("distanceMeters", 0)
        distance_miles = round(distance_meters * 0.000621371, 2)
        polyline_encoded = route.get("polyline", {}).get("encodedPolyline", "")

        # duration is returned as a string like "1230s"
        duration_raw = str(route.get("duration", "0s")).rstrip("s")
        try:
            duration_seconds = int(round(float(duration_raw)))
        except ValueError:
            duration_seconds = 0

        return {
            "success": True,
            "distance_miles": distance_miles,
            "distance_text": f"{distance_miles} mi",
            "duration_text": format_duration(duration_seconds),
            "duration_seconds": duration_seconds,
            "polyline": polyline_encoded,
            "error": None
        }

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            msg = err_body
        return {"success": False, "error": f"Routes API Error ({e.code}): {msg}"}
    except Exception as e:
        return {"success": False, "error": f"Routes API request error: {str(e)}"}


def get_google_maps_distance(origin: str, destination: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates driving distance and travel time between two addresses.
    Uses modern Google Routes API first, falling back to Distance Matrix API if needed.
    Ensures ZIP codes are present and accounts for nonexistent addresses.
    """
    key = api_key or get_api_key()
    if not key:
        return {
            "success": False,
            "error": "Google Maps API Key is missing. Please add GOOGLE_MAPS_API_KEY to your .env file."
        }

    # 1. Validate ZIP code presence for both addresses
    origin_valid, origin_err = validate_address_has_zip(origin, "Start address")
    if not origin_valid:
        return {"success": False, "error": origin_err}

    dest_valid, dest_err = validate_address_has_zip(destination, "Destination address")
    if not dest_valid:
        return {"success": False, "error": dest_err}

    # 2. Verify existence of both addresses via Geocoding API
    origin_check = check_address_exists(origin, key)
    if not origin_check["exists"]:
        return {"success": False, "error": f"Start location error: {origin_check['error']}"}

    dest_check = check_address_exists(destination, key)
    if not dest_check["exists"]:
        return {"success": False, "error": f"Destination location error: {dest_check['error']}"}

    formatted_origin = origin_check.get("formatted_address", origin)
    formatted_dest = dest_check.get("formatted_address", destination)
    origin_lat, origin_lng = origin_check.get("lat"), origin_check.get("lng")
    dest_lat, dest_lng = dest_check.get("lat"), dest_check.get("lng")

    # 3. Try modern Google Routes API first (recommended by Google for all new projects)
    if origin_lat is not None and dest_lat is not None:
        routes_res = get_routes_api_distance(origin_lat, origin_lng, dest_lat, dest_lng, key)
        if routes_res["success"]:
            return {
                "success": True,
                "mode": "address",
                "distance_miles": routes_res["distance_miles"],
                "distance_text": routes_res["distance_text"],
                "duration_text": routes_res["duration_text"],
                "duration_seconds": routes_res["duration_seconds"],
                "origin_input": origin,
                "origin_formatted": formatted_origin,
                "origin_coords": {"lat": origin_lat, "lng": origin_lng},
                "destination_input": destination,
                "destination_formatted": formatted_dest,
                "destination_coords": {"lat": dest_lat, "lng": dest_lng},
                "polyline": routes_res.get("polyline"),
                "error": None
            }
        # If Routes API failed with a permission/not-enabled error, try legacy Distance Matrix fallback
        routes_error = routes_res.get("error", "")
    else:
        routes_error = "Could not obtain coordinates for routing."

    # 4. Fallback: Call Google Maps Distance Matrix API
    encoded_origin = urllib.parse.quote(origin.strip())
    encoded_dest = urllib.parse.quote(destination.strip())
    url = (
        f"https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={encoded_origin}&destinations={encoded_dest}&units=imperial&key={key}"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GDG-DevFest-GasCalculator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        status = payload.get("status")
        if status != "OK":
            err_msg = payload.get("error_message", f"Status: {status}")
            # If both failed, provide informative instruction to enable Routes API
            return {
                "success": False,
                "error": (
                    f"Google Maps Routing Error: {err_msg}. "
                    "Please enable the 'Routes API' in your Google Cloud Console "
                    "(https://console.cloud.google.com/apis/library/routes.googleapis.com)."
                )
            }

        rows = payload.get("rows", [])
        if not rows or not rows[0].get("elements"):
            return {"success": False, "error": "No route data returned by Google Maps."}

        element = rows[0]["elements"][0]
        element_status = element.get("status")

        if element_status == "OK":
            distance_meters = element["distance"]["value"]
            distance_miles = round(distance_meters * 0.000621371, 2)
            distance_text = element["distance"].get("text", f"{distance_miles} mi")
            duration_text = element["duration"].get("text", "N/A")
            duration_seconds = element["duration"].get("value", 0)

            return {
                "success": True,
                "mode": "address",
                "distance_miles": distance_miles,
                "distance_text": distance_text,
                "duration_text": duration_text,
                "duration_seconds": duration_seconds,
                "origin_input": origin,
                "origin_formatted": formatted_origin,
                "origin_coords": {"lat": origin_lat, "lng": origin_lng},
                "destination_input": destination,
                "destination_formatted": formatted_dest,
                "destination_coords": {"lat": dest_lat, "lng": dest_lng},
                "polyline": routes_res.get("polyline"),
                "error": None
            }
        elif element_status == "ZERO_RESULTS":
            return {
                "success": False,
                "error": f"No driving route could be found between '{formatted_origin}' and '{formatted_dest}'."
            }
        else:
            return {
                "success": False,
                "error": f"Unable to compute route: {element_status}"
            }

    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Network error contacting routing APIs: {str(e)}. (Routes API also reported: {routes_error})"
        }
    except Exception as e:
        return {"success": False, "error": f"Unexpected error calculating distance: {str(e)}"}


def validate_manual_miles(miles_input: Any) -> Dict[str, Any]:
    """
    Validates user-typed manual mileage input.
    Requires the user to explicitly type a valid positive number.
    """
    if miles_input is None:
        return {"success": False, "error": "Miles input is required. Please type the number of miles."}

    # Handle string input
    if isinstance(miles_input, str):
        cleaned = miles_input.strip()
        if not cleaned:
            return {"success": False, "error": "Miles field cannot be empty. Please type the number of miles."}
        try:
            miles_val = float(cleaned)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid mileage format: '{cleaned}'. Please type a valid number (e.g., 25 or 142.5)."
            }
    elif isinstance(miles_input, (int, float)):
        miles_val = float(miles_input)
    else:
        return {"success": False, "error": "Invalid mileage input type. Please type a number."}

    # Value checks
    if miles_val <= 0:
        return {"success": False, "error": "Miles must be a positive number greater than 0."}

    if miles_val > 25000:
        return {"success": False, "error": "Miles value exceeds maximum reasonable distance (25,000 miles)."}

    rounded_miles = round(miles_val, 2)
    return {
        "success": True,
        "mode": "manual",
        "distance_miles": rounded_miles,
        "distance_text": f"{rounded_miles:.2f} mi",
        "duration_text": "N/A (Manually specified)",
        "duration_seconds": 0,
        "origin_formatted": "Custom Start",
        "destination_formatted": "Custom Destination",
        "origin_input": None,
        "destination_input": None,
        "error": None
    }


def calculate_distance(
    mode: str,
    origin: str = "",
    destination: str = "",
    manual_miles: Any = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unified entry point for distance calculation.
    Supports both 'address' mode (Google Maps API) and 'manual' mode (typed miles).
    Modularly designed for easy expansion by future app sections (Gas Prices, Carpool, Map).
    """
    normalized_mode = (mode or "").strip().lower()

    if normalized_mode == "manual":
        return validate_manual_miles(manual_miles)
    elif normalized_mode == "address":
        return get_google_maps_distance(origin, destination, api_key=api_key)
    else:
        return {
            "success": False,
            "error": f"Invalid mode '{mode}'. Choose 'address' or 'manual'."
        }
