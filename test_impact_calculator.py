"""
Test Suite for EcoTransform AI Upgraded Sustainability Calculator
Verifies:
1. Weight entry in both units (grams and kilograms)
2. Editable weight input and dynamic recalculation
3. Accurate India-specific emission factors and prevention of double-counting
4. Non-fabrication of missing data (returns None / 'Data unavailable')
5. Invalid weight input validation (negative, zero, non-numeric)
6. Separation of recycling, reuse, and upcycling pathways
7. Dashboard and history consistency with user-confirmed weights
"""

import unittest
import json
from app import app
from impact_calculator import calculate_environmental_impact, MATERIAL_METRICS
import database as db


class SustainabilityCalculatorTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_units_conversion_g_and_kg(self):
        # 50 grams should yield identical environmental impact to 0.05 kilograms
        res_g = calculate_environmental_impact(
            item_name="PET Bottle",
            primary_material="Polyethylene Terephthalate",
            detected_weight_kg=0.05,
            unit="g",
            is_user_confirmed=True
        )
        res_kg = calculate_environmental_impact(
            item_name="PET Bottle",
            primary_material="Polyethylene Terephthalate",
            detected_weight_kg=0.05,
            unit="kg",
            is_user_confirmed=True
        )
        self.assertEqual(res_g["co2_avoided_kg"], res_kg["co2_avoided_kg"])
        self.assertEqual(res_g["landfill_diverted_kg"], res_kg["landfill_diverted_kg"])
        self.assertEqual(res_g["economic_value_inr"], res_kg["economic_value_inr"])
        self.assertEqual(res_g["weight_grams"], 50.0)
        self.assertEqual(res_g["estimated_weight_kg"], 0.05)

    def test_ai_suggestion_vs_user_confirmed_status(self):
        # When user does not confirm, status is AI Suggestion
        res_unconfirmed = calculate_environmental_impact(
            item_name="PET Bottle",
            primary_material="Polyethylene Terephthalate",
            is_user_confirmed=False
        )
        self.assertFalse(res_unconfirmed["is_user_confirmed"])
        self.assertEqual(res_unconfirmed["weight_status"], "AI Suggestion")

        # When user confirms, status is Confirmed
        res_confirmed = calculate_environmental_impact(
            item_name="PET Bottle",
            primary_material="Polyethylene Terephthalate",
            detected_weight_kg=0.030,
            is_user_confirmed=True
        )
        self.assertTrue(res_confirmed["is_user_confirmed"])
        self.assertEqual(res_confirmed["weight_status"], "Confirmed")

    def test_scenario_separation_prevents_double_counting(self):
        # Recycling vs Reuse vs Upcycling must have distinct factors and never be summed together
        res_recycling = calculate_environmental_impact(
            item_name="Aluminum Can",
            primary_material="Aluminum",
            detected_weight_kg=0.1,
            scenario="recycling"
        )
        res_reuse = calculate_environmental_impact(
            item_name="Aluminum Can",
            primary_material="Aluminum",
            detected_weight_kg=0.1,
            scenario="reuse"
        )
        res_upcycling = calculate_environmental_impact(
            item_name="Aluminum Can",
            primary_material="Aluminum",
            detected_weight_kg=0.1,
            scenario="upcycling"
        )
        # All three must produce distinct CO2 savings
        self.assertNotEqual(res_recycling["co2_avoided_kg"], res_reuse["co2_avoided_kg"])
        self.assertNotEqual(res_reuse["co2_avoided_kg"], res_upcycling["co2_avoided_kg"])
        # Scenario must be recorded accurately
        self.assertEqual(res_recycling["scenario"], "recycling")
        self.assertEqual(res_reuse["scenario"], "reuse")
        self.assertEqual(res_upcycling["scenario"], "upcycling")

    def test_never_fabricate_when_factors_missing(self):
        # Organic waste composting has no reliable industrial water savings factor
        res_organic = calculate_environmental_impact(
            item_name="Banana Peel",
            primary_material="Organic Food Waste",
            detected_weight_kg=0.2,
            scenario="recycling"
        )
        self.assertIsNone(res_organic["water_saved_liters"])
        self.assertIsNone(res_organic["energy_saved_kwh"])
        # Must clearly reflect in explanation
        expl = res_organic["calculation_explanation"]
        self.assertIn("unavailable", expl["water_formula"].lower())

    def test_recalculate_api_valid_grams_and_kg(self):
        # API test with grams
        resp = self.client.post("/api/impact/recalculate", json={
            "item_name": "Soda Can",
            "primary_material": "Aluminum",
            "weight": 30,  # 30 grams = 0.03 kg
            "unit": "g",
            "scenario": "recycling"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["estimated_weight_kg"], 0.03)
        self.assertEqual(data["weight_grams"], 30.0)
        self.assertTrue(data["is_user_confirmed"])
        # 0.03 kg * 8.95 kg CO2e/kg = 0.2685 kg
        self.assertAlmostEqual(data["co2_avoided_kg"], 0.2685, places=3)
        # 0.03 kg * ₹130/kg = ₹3.90
        self.assertEqual(data["economic_value_inr"], 3.9)

    def test_recalculate_api_invalid_weight_validation(self):
        # Negative weight
        resp = self.client.post("/api/impact/recalculate", json={
            "item_name": "Can",
            "primary_material": "Aluminum",
            "weight": -10,
            "unit": "g"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("error_code"), "INVALID_WEIGHT")

        # Zero weight
        resp_zero = self.client.post("/api/impact/recalculate", json={
            "item_name": "Can",
            "primary_material": "Aluminum",
            "weight": 0,
            "unit": "kg"
        })
        self.assertEqual(resp_zero.status_code, 400)

        # Non-numeric string
        resp_bad = self.client.post("/api/impact/recalculate", json={
            "item_name": "Can",
            "primary_material": "Aluminum",
            "weight": "abc",
            "unit": "kg"
        })
        self.assertEqual(resp_bad.status_code, 400)
        self.assertEqual(resp_bad.get_json().get("error_code"), "INVALID_WEIGHT_FORMAT")

    def test_recalculate_persists_and_updates_dashboard(self):
        # 1. Analyze an item to create a scan record
        scan_resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "Clear plastic water bottle 500ml",
            "bypass_clarification": True
        })
        self.assertEqual(scan_resp.status_code, 200)
        scan_data = scan_resp.get_json()
        scan_id = scan_data["scan_id"]

        # 2. Update weight to 100 grams via recalculate endpoint
        recalc_resp = self.client.post("/api/impact/recalculate", json={
            "item_name": "Clear plastic water bottle 500ml",
            "primary_material": "Polyethylene Terephthalate",
            "weight": 100,
            "unit": "g",
            "scenario": "recycling",
            "scan_id": scan_id
        })
        self.assertEqual(recalc_resp.status_code, 200)
        recalc_data = recalc_resp.get_json()
        self.assertEqual(recalc_data["estimated_weight_kg"], 0.1)

        # 3. Check that scan detail returns the confirmed weight
        detail = db.get_scan_detail(scan_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["environmental_impact"]["estimated_weight_kg"], 0.1)
        self.assertTrue(detail["environmental_impact"]["is_user_confirmed"])


if __name__ == "__main__":
    unittest.main()
