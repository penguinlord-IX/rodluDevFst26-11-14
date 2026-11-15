"""
test_trip_route.py - Modular unit tests for trip route and distance validation.
Tests input validation, ZIP code requirements, manual mileage typing, and error handling.
"""

import unittest
from route_service import (
    extract_zip_code,
    validate_address_has_zip,
    validate_manual_miles,
    calculate_distance,
    get_google_maps_distance
)


class TestTripRoute(unittest.TestCase):

    def test_zip_code_extraction(self):
        """Test extraction of 5-digit and 5+4 ZIP codes."""
        self.assertEqual(extract_zip_code("1600 Amphitheatre Pkwy, Mountain View, CA 94043"), "94043")
        self.assertEqual(extract_zip_code("1 Infinite Loop, Cupertino, CA 95014-2083"), "95014-2083")
        self.assertIsNone(extract_zip_code("123 Main Street, San Jose, CA"))
        self.assertIsNone(extract_zip_code(""))

    def test_address_zip_validation(self):
        """Ensure missing ZIP code produces clear validation error."""
        valid, msg = validate_address_has_zip("123 Main St, Austin, TX 78701", "Start address")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

        invalid, err_msg = validate_address_has_zip("123 Main St, Austin, TX", "Start address")
        self.assertFalse(invalid)
        self.assertIn("must include a valid 5-digit ZIP code", err_msg)

        empty_valid, empty_err = validate_address_has_zip("", "Destination address")
        self.assertFalse(empty_valid)
        self.assertIn("cannot be empty", empty_err)

    def test_manual_miles_valid_typed_inputs(self):
        """Ensure valid typed numeric strings are parsed and formatted properly."""
        res = validate_manual_miles("42.5")
        self.assertTrue(res["success"])
        self.assertEqual(res["distance_miles"], 42.5)
        self.assertEqual(res["mode"], "manual")

        res_int = validate_manual_miles("100")
        self.assertTrue(res_int["success"])
        self.assertEqual(res_int["distance_miles"], 100.0)

    def test_manual_miles_invalid_inputs(self):
        """Ensure invalid or negative typed values are rejected with helpful errors."""
        # Empty input
        res_empty = validate_manual_miles("")
        self.assertFalse(res_empty["success"])
        self.assertIn("cannot be empty", res_empty["error"])

        # Non-numeric input
        res_text = validate_manual_miles("twenty miles")
        self.assertFalse(res_text["success"])
        self.assertIn("Invalid mileage format", res_text["error"])

        # Zero or negative
        res_zero = validate_manual_miles("0")
        self.assertFalse(res_zero["success"])
        self.assertIn("greater than 0", res_zero["error"])

        res_neg = validate_manual_miles("-15")
        self.assertFalse(res_neg["success"])
        self.assertIn("greater than 0", res_neg["error"])

        # Unreasonable distance
        res_large = validate_manual_miles("999999")
        self.assertFalse(res_large["success"])
        self.assertIn("exceeds maximum reasonable distance", res_large["error"])

    def test_missing_api_key_error(self):
        """Ensure appropriate error is returned when Google Maps API key is not configured."""
        res = get_google_maps_distance(
            "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
            "1 Infinite Loop, Cupertino, CA 95014",
            api_key=""
        )
        self.assertFalse(res["success"])
        self.assertIn("Google Maps API Key is missing", res["error"])

    def test_city_candidate_extraction(self):
        """Test extraction of city candidates from address string."""
        from route_service import extract_city_candidates
        words = extract_city_candidates("Santa Cruz 91803", "91803")
        self.assertEqual(words, ["Santa", "Cruz"])

        words2 = extract_city_candidates("123 Ocean St, Santa Cruz, CA 91803", "91803", state_short="CA")
        self.assertEqual(words2, ["Ocean", "Santa", "Cruz"])

    def test_unified_calculate_distance(self):
        """Ensure calculate_distance correctly routes manual mode requests."""
        res = calculate_distance(mode="manual", manual_miles="65.2")
        self.assertTrue(res["success"])
        self.assertEqual(res["distance_miles"], 65.2)

        res_invalid_mode = calculate_distance(mode="teleport")
        self.assertFalse(res_invalid_mode["success"])
        self.assertIn("Invalid mode", res_invalid_mode["error"])


if __name__ == "__main__":
    unittest.main()
