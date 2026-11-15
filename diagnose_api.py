"""
diagnose_api.py - Safe diagnostic script for Google Maps API issues.
Tests the API connection and reports the exact response from Google without revealing your secret key.
"""

import sys
from route_service import get_api_key, check_address_exists, get_google_maps_distance


def run_diagnostics():
    print("=" * 65)
    print(" Google Maps API Diagnostics for GDG DevFest")
    print("=" * 65)

    # 1. Check if API key is detected
    key = get_api_key()
    if not key:
        print("\n❌ ISSUE DETECTED: API key is missing or not detected.")
        print("  - Make sure your .env file has: GOOGLE_MAPS_API_KEY=AIzaSy...")
        print("  - Ensure there are no spaces before the '=' sign.")
        return

    key_len = len(key)
    masked = key[:4] + "*" * (key_len - 8) + key[-4:] if key_len >= 8 else "****"
    print(f"\n✅ API Key found in environment/file: {masked} (length: {key_len})")

    # 2. Test Geocoding API & ZIP Correspondence Validation
    print("\n--- Testing Geocoding & City-ZIP Validation ---")
    test_address = "1600 Amphitheatre Pkwy, Mountain View, CA 94043"
    print(f"1. Valid address test: '{test_address}'...")
    geo_res = check_address_exists(test_address, key)

    if geo_res.get("exists"):
        print("   ✅ Valid address accepted and resolved correctly!")
        print(f"      Resolved: {geo_res.get('formatted_address')}")
    else:
        print(f"   ❌ Error: {geo_res.get('error')}")

    mismatched_test = "Santa Cruz, CA 91803"
    print(f"\n2. Mismatched address test: '{mismatched_test}' (91803 is Alhambra, not Santa Cruz)...")
    mismatch_res = check_address_exists(mismatched_test, key)

    if not mismatch_res.get("exists"):
        print("   ✅ Correctly caught and rejected mismatch!")
        print(f"      Message shown to user: {mismatch_res.get('error')}")
    else:
        print("   ❌ Failed to reject mismatch: address was accepted as valid.")

    # 3. Test Routing (Routes API / Distance Matrix)
    print("\n--- Testing Route Calculation (Routes API) ---")
    dest_address = "1 Infinite Loop, Cupertino, CA 95014"
    print(f"Pinging Route Calculation between test locations...")
    dist_res = get_google_maps_distance(test_address, dest_address, api_key=key)

    if dist_res.get("success"):
        print("✅ Route calculation is working properly!")
        print(f"   Distance: {dist_res.get('distance_miles')} miles ({dist_res.get('distance_text')})")
        print(f"   Duration: {dist_res.get('duration_text')}")
    else:
        print("❌ Route Calculation Error:")
        print(f"   {dist_res.get('error')}")

    print("\n" + "=" * 65)
    print(" QUICK FIX FOR 'Legacy API / Routes API':")
    print("=" * 65)
    print("Google has transitioned new projects to the 'Routes API'.")
    print("1. Visit: https://console.cloud.google.com/apis/library/routes.googleapis.com")
    print("2. Make sure your project is selected at the top.")
    print("3. Click 'ENABLE' on Routes API.")
    print("4. If your key has API restrictions, make sure 'Routes API' is checked!")
    print("=" * 65)


if __name__ == "__main__":
    run_diagnostics()
