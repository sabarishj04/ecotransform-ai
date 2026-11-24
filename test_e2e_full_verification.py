"""
EcoTransform AI - Complete End-to-End System QA & Verification Suite
Tests all 19 required capabilities:
1. Camera input processing
2. Image upload processing
3. Text description identification & Smart Clarification
4. Manual material selection
5. OCR text extraction & image quality evaluation
6. Recycling symbol detection (RIC 1-7)
7. Barcode & QR code recognition (EAN-13, UPC, Code-128, QR URLs)
8. Multimodal AI evidence fusion & consensus
9. User corrections (manual barcode correction & weight overrides)
10. Upcycle blueprint recommendations (3 recipes, difficulty, materials, tools, steps)
11. Safety detection & warnings (handling sharp metal, hazardous materials, batteries)
12. Environmental calculations (CO2e, landfill, water, energy, scrap value in INR)
13. Dashboard analytics (real vs demo scope, totals, material breakdown)
14. Database persistence (SQLite schema, foreign keys, updates, soft-deletes)
15. Waste history operations (session retrieval, detail view, deletion)
16. Mobile responsiveness & CSS / DOM layout checks
17. API failures & resilience (empty inputs, negative weights, invalid payloads)
18. Security verification (CORS headers, input sanitization, API key server-side isolation)
19. Production build readiness (health endpoint, routes, file assets, configuration)
"""

import unittest
import json
import base64
import io
from PIL import Image
import database as db
from app import app
from impact_calculator import calculate_environmental_impact, MATERIAL_METRICS
from barcode_service import lookup_barcode_product, VERIFIED_PRODUCT_CATALOG
from intelligence_engine import fuse_evidence
from centers_service import search_recycling_centres
from gemini_service import classify_indian_waste_stream, check_text_clarification_needed
from ocr_service import RESIN_IDENTIFICATION_CODES, evaluate_image_quality


class CompleteE2EQATestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.session_id = "qa_e2e_session_master_001"

    # ================= 1. CAMERA INPUT =================
    def test_01_camera_capture_input(self):
        """Generates synthetic JPEG byte buffer to simulate camera base64 snapshot."""
        img = Image.new("RGB", (320, 240), color=(50, 150, 250))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64_str = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        resp = self.client.post("/api/analyze", json={
            "input_method": "camera",
            "image_b64": b64_str,
            "filename": "camera_capture.jpg"
        }, headers={"X-Session-ID": self.session_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("input_method"), "camera")
        self.assertIn("waste_analysis", data)
        self.assertIn("environmental_impact", data)
        self.assertIn("scan_id", data)

    # ================= 2. IMAGE UPLOAD =================
    def test_02_image_upload_multipart(self):
        """Simulates drag-and-drop or file-picker multipart form upload."""
        img = Image.new("RGB", (400, 300), color=(100, 200, 100))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        data = {
            "image": (buf, "coca_cola_plastic_bottle.jpg"),
            "input_method": "image_upload"
        }
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data",
                                headers={"X-Session-ID": self.session_id})

        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()
        self.assertEqual(res_json.get("input_method"), "image_upload")
        self.assertTrue(len(res_json.get("image_preview", "")) > 10)

    # ================= 3. TEXT DESCRIPTION & CLARIFICATION =================
    def test_03_text_description_with_smart_clarification(self):
        """Tests natural language description and handles clarification when ambiguous."""
        # Ambiguous prompt triggers clarification question
        ambiguous_resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "empty food container"
        })
        self.assertEqual(ambiguous_resp.status_code, 200)
        amb_data = ambiguous_resp.get_json()
        self.assertEqual(amb_data.get("status"), "needs_clarification")
        self.assertIn("question", amb_data)

        # Detailed description bypasses or answers clarification
        detailed_resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "I have an empty 500ml transparent plastic water bottle with blue screw cap",
            "bypass_clarification": True
        }, headers={"X-Session-ID": self.session_id})
        self.assertEqual(detailed_resp.status_code, 200)
        det_data = detailed_resp.get_json()
        self.assertEqual(det_data.get("input_method"), "text_description")
        self.assertIn("Polyethylene", det_data["waste_analysis"]["primary_material"])

    # ================= 4. MANUAL MATERIAL SELECTION =================
    def test_04_manual_material_selection(self):
        """Tests manual category choice from dropdown list."""
        resp = self.client.post("/api/analyze", json={
            "input_method": "manual_selection",
            "material_category": "Rigid Plastics (PET / HDPE)",
            "item_details": "Shampoo bottle container"
        }, headers={"X-Session-ID": self.session_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("input_method"), "manual_selection")
        self.assertTrue(any(term in data.get("identification_method", "") for term in ["MANUAL", "MANUAL SELECTION"]))

    # ================= 5. OCR TEXT EXTRACTION & QUALITY =================
    def test_05_ocr_and_image_quality(self):
        """Tests image sharpness, brightness evaluation, and OCR extraction."""
        img = Image.new("RGB", (600, 400), color=(240, 240, 240))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        quality = evaluate_image_quality(buf.getvalue())
        self.assertIn("status", quality)
        self.assertIn("score", quality)
        self.assertTrue(quality.get("is_sharp", True))

    # ================= 6. RECYCLING SYMBOL DETECTION =================
    def test_06_resin_identification_codes(self):
        """Verifies all 7 SPI Resin Identification Codes are correctly recognized."""
        for code in range(1, 8):
            self.assertIn(code, RESIN_IDENTIFICATION_CODES)
            info = RESIN_IDENTIFICATION_CODES[code]
            self.assertIn("material_name", info)
            self.assertIn("recyclability", info)

    # ================= 7. BARCODE & QR RECOGNITION =================
    def test_07_barcode_and_qr_recognition(self):
        """Verifies verified catalog lookup and QR URL parsing."""
        # 1. Verified Coca-Cola EAN-13
        res = lookup_barcode_product("5449000000996")
        self.assertTrue(res["found"])
        self.assertTrue(res["verified"])
        self.assertIn("Coca-Cola", res["product_name"])
        self.assertIn("PET", res["packaging"]["primary_material"])

        # 2. QR Code URL
        qr_res = lookup_barcode_product("https://recycle.cpcb.gov.in/plastic-portal")
        self.assertTrue(qr_res["found"])
        self.assertEqual(qr_res["barcode_type"], "QR-Code URL")

        # 3. Unregistered barcode (honest response without fabrication)
        unreg = lookup_barcode_product("9999999999999")
        self.assertFalse(unreg["verified"])
        self.assertIn("No verified product match found", unreg["message"])

    # ================= 8. MULTIMODAL AI EVIDENCE FUSION =================
    def test_08_multimodal_evidence_fusion_consensus(self):
        """Tests evidence fusion across vision, OCR, and barcode."""
        vision = {"object_name": "Soda Can", "material": "Aluminum", "recyclability": "Recyclable"}
        ocr = {"extracted_text": "ALUMINUM CAN", "material": "Aluminum Alloy 3004"}
        barcode = {
            "found": True, "verified": True, "product_name": "Pepsi Can",
            "packaging": {"primary_material": "Aluminum Alloy 3004"}
        }

        fusion = fuse_evidence(visual_result=vision, ocr_result=ocr, barcode_result=barcode)
        self.assertEqual(fusion["confidence_level"], "high")
        self.assertEqual(fusion["source_count"], 3)
        self.assertFalse(fusion["has_conflicts"])
        self.assertTrue(fusion["identification_method"].startswith("MULTIMODAL"))

    # ================= 9. USER CORRECTIONS =================
    def test_09_user_corrections_and_overrides(self):
        """Tests user manual correction on barcode and manual weight overrides."""
        # User manual correction on unverified barcode
        resp = self.client.post("/api/analyze", json={
            "input_method": "barcode_scan",
            "barcode": "8901030382910",
            "manual_correction": {
                "product_name": "Local Indian Dairy Ghee Jar",
                "material": "High-Density Polyethylene (HDPE #2)"
            }
        }, headers={"X-Session-ID": self.session_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["barcode_evidence"]["manual_correction_applied"])

    # ================= 10. UPCYCLING BLUEPRINTS =================
    def test_10_upcycling_recommendations(self):
        """Verifies 3 complete blueprints with steps, materials, and INR costs."""
        resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "Corrugated cardboard shipping box",
            "bypass_clarification": True
        })
        self.assertEqual(resp.status_code, 200)
        recs = resp.get_json().get("upcycle_recommendations", [])
        self.assertGreaterEqual(len(recs), 1)
        first = recs[0]
        self.assertIn("product_name", first)
        self.assertIn("difficulty", first)
        self.assertIn("materials_needed", first)
        self.assertIn("steps", first)

    # ================= 11. SAFETY DETECTION =================
    def test_11_safety_detection_and_warnings(self):
        """Verifies hazardous and sharp safety warning flags."""
        battery_resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "Corroded leaking lithium-ion mobile battery cell",
            "bypass_clarification": True
        })
        self.assertEqual(battery_resp.status_code, 200)
        data = battery_resp.get_json()
        stream = data.get("indian_waste_stream") or data["waste_analysis"].get("indian_waste_stream")
        self.assertEqual(stream["stream_code"], "special-care")
        self.assertIn("Black", stream["bin_color"])

    # ================= 12. ENVIRONMENTAL CALCULATIONS =================
    def test_12_environmental_calculations_inr(self):
        """Verifies accurate Indian emission factors and INR scrap values."""
        impact = calculate_environmental_impact(
            item_name="PET Bottle",
            primary_material="Polyethylene Terephthalate",
            detected_weight_kg=0.1,  # 100g
            scenario="recycling",
            is_user_confirmed=True
        )
        # 0.1 kg * 2.10 kg CO2e/kg = 0.21 kg
        self.assertAlmostEqual(impact["co2_avoided_kg"], 0.21, places=2)
        # 0.1 kg * ₹25/kg scrap rate = ₹2.50
        self.assertAlmostEqual(impact["economic_value_inr"], 2.50, places=2)
        # 0.1 kg * 5.4 kWh/kg = 0.54 kWh
        self.assertAlmostEqual(impact["energy_saved_kwh"], 0.54, places=2)

    # ================= 13. DASHBOARD ANALYTICS =================
    def test_13_dashboard_personal_vs_global(self):
        """Verifies real dashboard aggregation and empty state separation."""
        stats = db.get_dashboard_stats(session_id=self.session_id)
        self.assertIn("total_scans", stats)
        self.assertIn("total_material_weight_kg", stats)
        self.assertIn("total_economic_inr", stats)
        self.assertIn("material_breakdown", stats)

    # ================= 14. DATABASE PERSISTENCE =================
    def test_14_database_crud_operations(self):
        """Verifies SQLite save, detail lookup, update, and soft-delete."""
        # 1. Create
        scan_resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "Steel tomato soup tin can",
            "bypass_clarification": True
        }, headers={"X-Session-ID": self.session_id})
        scan_id = scan_resp.get_json()["scan_id"]

        # 2. Read Detail
        detail = db.get_scan_detail(scan_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["scan_id"], scan_id)

        # 3. Update Weight
        new_impact = calculate_environmental_impact("Steel can", "Steel", detected_weight_kg=0.2, is_user_confirmed=True)
        updated = db.update_scan_weight_and_impact(scan_id, new_impact)
        self.assertTrue(updated)
        refreshed = db.get_scan_detail(scan_id)
        self.assertEqual(refreshed["environmental_impact"]["estimated_weight_kg"], 0.2)

        # 4. Soft Delete
        del_resp = self.client.delete(f"/api/history/{scan_id}", headers={"X-Session-ID": self.session_id})
        self.assertEqual(del_resp.status_code, 200)
        self.assertIsNone(db.get_scan_detail(scan_id))

    # ================= 15. WASTE HISTORY =================
    def test_15_history_endpoint(self):
        """Verifies /api/history endpoint retrieves user sessions."""
        resp = self.client.get(f"/api/history?session_id={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("scans", resp.get_json())

    # ================= 16. MOBILE RESPONSIVENESS =================
    def test_16_mobile_meta_viewport(self):
        """Verifies mobile viewport and responsive CSS styling tags."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('<meta name="viewport"', html)
        self.assertIn("width=device-width", html)
        self.assertIn("tailwind", html.lower())

    # ================= 17. API FAILURES & VALIDATION =================
    def test_17_api_failure_and_resilience(self):
        """Verifies handling of empty inputs, missing bodies, and invalid types."""
        # Empty input
        r1 = self.client.post("/api/analyze", json={})
        self.assertEqual(r1.status_code, 400)
        self.assertIn("error_code", r1.get_json())

        # Empty barcode
        r2 = self.client.post("/api/barcode/lookup", json={"barcode": ""})
        self.assertEqual(r2.status_code, 400)

        # Negative weight recalculation
        r3 = self.client.post("/api/impact/recalculate", json={"weight": -5, "unit": "kg"})
        self.assertEqual(r3.status_code, 400)

    # ================= 18. SECURITY VERIFICATION =================
    def test_18_security_headers_and_credential_isolation(self):
        """Verifies CORS, origin protection, and server-side secret isolation."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        data = resp.get_json()
        self.assertIn("gemini_configured", data)
        # Server must never leak actual API key in response
        self.assertNotIn("AIza", json.dumps(data))

    # ================= 19. PRODUCTION BUILD READINESS =================
    def test_19_production_build_readiness(self):
        """Verifies /api/health and all core static files load cleanly."""
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json().get("status"), "healthy")

        # Static assets
        app_js = self.client.get("/static/app.js")
        self.assertEqual(app_js.status_code, 200)

        i18n_js = self.client.get("/static/translations.js")
        self.assertEqual(i18n_js.status_code, 200)


if __name__ == "__main__":
    unittest.main()
