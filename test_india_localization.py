"""
Test Suite for EcoTransform AI India Adaptation
Verifies:
1. Indian Rupee (₹) currency everywhere
2. Indian Solid Waste Management (SWM 2016) stream classifications:
   - Wet Waste (Green Bin / ஈரக் கழிவு)
   - Dry Waste (Blue Bin / உலர் கழிவு)
   - Sanitary Waste (Red / சுகாதாரக் கழிவு)
   - Special-Care / Domestic Hazardous (Black / சிறப்புக் கழிவு)
3. Verified Recycling Centres endpoint (/api/centres) with city and stream filters
4. Real stored dashboard data vs demo data handling
5. Bilingual English and Tamil metadata support
"""

import unittest
import json
from app import app
from gemini_service import classify_indian_waste_stream
from centers_service import search_recycling_centres, VERIFIED_RECYCLING_CENTRES
import database as db


class IndiaLocalizationTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_swm_2016_wet_waste_classification(self):
        res = classify_indian_waste_stream(item_name="Vegetable kitchen peelings", material="Organic Food Waste")
        self.assertEqual(res["stream_code"], "wet")
        self.assertEqual(res["bin_color"], "Green Bin")
        self.assertIn("பச்சை தொட்டி", res["bin_color_ta"])
        self.assertIn("ஈரக் கழிவு", res["stream_name_ta"])

    def test_swm_2016_dry_waste_classification(self):
        res = classify_indian_waste_stream(item_name="Plastic Water Bottle", material="Polyethylene Terephthalate")
        self.assertEqual(res["stream_code"], "dry")
        self.assertEqual(res["bin_color"], "Blue Bin")
        self.assertIn("நீல தொட்டி", res["bin_color_ta"])
        self.assertIn("உலர் கழிவு", res["stream_name_ta"])

    def test_swm_2016_sanitary_waste_classification(self):
        res = classify_indian_waste_stream(item_name="Baby diaper", material="Cellulose / SAP Polymer")
        self.assertEqual(res["stream_code"], "sanitary")
        self.assertEqual(res["stream_code"], "sanitary")
        self.assertIn("Red", res["bin_color"])
        self.assertIn("சிவப்பு", res["bin_color_ta"])
        self.assertIn("சுகாதாரக் கழிவு", res["stream_name_ta"])

    def test_swm_2016_special_care_hazardous_waste_classification(self):
        res = classify_indian_waste_stream(item_name="AA Alkaline Battery", material="Zinc-Manganese / Alkaline", is_hazardous=True)
        self.assertEqual(res["stream_code"], "special-care")
        self.assertIn("Black", res["bin_color"])
        self.assertIn("கருப்பு", res["bin_color_ta"])
        self.assertIn("சிறப்பு கவனம்", res["stream_name_ta"])

    def test_recycling_centres_api_endpoint(self):
        resp = self.client.get("/api/centres")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("centres", data)
        self.assertGreater(data["total"], 0)
        self.assertIn("Chennai", data["supported_cities"])

    def test_recycling_centres_filtering_by_city_and_stream(self):
        # Filter Chennai
        chennai_results = search_recycling_centres(city="Chennai")
        self.assertTrue(all("chennai" in c["city"].lower() for c in chennai_results))
        self.assertGreater(len(chennai_results), 0)

        # Filter e-waste / special-care
        ewaste_results = search_recycling_centres(stream="special-care")
        self.assertTrue(all("special-care" in c["accepted_streams"] for c in ewaste_results))

    def test_dashboard_real_data_separation(self):
        # Unique session with 0 scans
        unique_session = "test_empty_session_9999"
        resp = self.client.get(f"/api/dashboard/stats?session_id={unique_session}&scope=personal")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_scans"], 0)
        self.assertEqual(data["total_material_weight_kg"], 0.0)
        self.assertTrue(data.get("is_empty", True))

        # Global scope should report real cumulative totals
        resp_global = self.client.get("/api/dashboard/stats?scope=global")
        self.assertEqual(resp_global.status_code, 200)
        global_data = resp_global.get_json()
        self.assertIn("total_economic_inr", global_data)
        self.assertIn("total_scans", global_data)

    def test_analyze_endpoint_returns_indian_stream_and_inr(self):
        resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "Used aluminum soda can 330ml",
            "bypass_clarification": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("waste_analysis", data)
        ans = data["waste_analysis"]
        self.assertIn("indian_waste_stream", ans)
        stream = ans["indian_waste_stream"]
        self.assertEqual(stream["stream_code"], "dry")
        # Impact contains INR
        self.assertIn("environmental_impact", data)
        imp = data["environmental_impact"]
        self.assertIsNotNone(imp["economic_value_inr"])
        self.assertGreater(imp["economic_value_inr"], 0)


if __name__ == "__main__":
    unittest.main()
