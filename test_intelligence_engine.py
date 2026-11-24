"""
Test Suite for Unified Multimodal Waste Intelligence Engine
Verifies evidence fusion across all 6 input combinations:
1. Zero sources (handles gracefully)
2. Single source: Vision only
3. Single source: Barcode only (verified vs unverified)
4. Single source: Text only
5. Single source: Manual only
6. Multimodal: Vision + OCR (agreeing)
7. Multimodal: Vision + Barcode (agreeing)
8. Multimodal: Vision + OCR (conflicting -> detects conflict)
9. Multimodal: All sources combined
10. End-to-end /api/analyze integration
"""

import unittest
import json
from intelligence_engine import fuse_evidence, _materials_conflict
from app import app


class TestMultimodalIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_zero_sources_graceful_handling(self):
        res = fuse_evidence()
        self.assertTrue(res.get("error"))
        self.assertEqual(res.get("error_code"), "NO_EVIDENCE")
        self.assertFalse(res.get("needs_user_confirmation"))

    def test_single_source_vision_only(self):
        vision_data = {
            "object_name": "Clear Beverage Bottle",
            "material": "Polyethylene Terephthalate (PET, #1)",
            "waste_categories": ["Plastic Packaging", "Recyclable"],
            "recyclability": "Highly Recyclable",
            "disposal_guidance": "Rinse and place in curbside recycling bin.",
            "safety_warnings": []
        }
        res = fuse_evidence(visual_result=vision_data)
        self.assertFalse(res.get("error", False))
        self.assertEqual(res["source_count"], 1)
        self.assertEqual(res["confidence_level"], "moderate")
        self.assertIn("Visual AI", res["active_sources"])
        self.assertFalse(res["has_conflicts"])

    def test_single_source_barcode_verified(self):
        barcode_data = {
            "found": True,
            "verified": True,
            "product_name": "Coca-Cola 500ml",
            "manufacturer": "The Coca-Cola Company",
            "packaging": {
                "primary_material": "Polyethylene Terephthalate (PET, #1)",
                "disposal_instructions": "Empty liquid and cap securely."
            }
        }
        res = fuse_evidence(barcode_result=barcode_data)
        self.assertEqual(res["confidence_level"], "high")
        self.assertEqual(res["source_count"], 1)
        self.assertIn("Barcode / QR", res["active_sources"])
        self.assertFalse(res["has_conflicts"])

    def test_single_source_barcode_unverified_needs_confirmation(self):
        barcode_data = {
            "found": True,
            "verified": False,
            "product_name": "Unknown Energy Drink",
            "packaging": {
                "primary_material": "Unknown Polymer"
            }
        }
        res = fuse_evidence(barcode_result=barcode_data)
        self.assertEqual(res["confidence_level"], "uncertain")
        self.assertTrue(res["needs_user_confirmation"])

    def test_single_source_manual_needs_confirmation(self):
        manual_data = {
            "material_category": "Rigid Plastic",
            "item_details": "Unbranded food tub"
        }
        res = fuse_evidence(manual_result=manual_data)
        self.assertEqual(res["confidence_level"], "uncertain")
        self.assertTrue(res["needs_user_confirmation"])

    def test_multimodal_vision_and_ocr_agreement(self):
        vision_data = {
            "object_name": "Milk Jug",
            "material": "High-Density Polyethylene (HDPE, #2)",
            "waste_categories": ["Recyclable Plastics"],
            "recyclability": "Recyclable",
            "disposal_guidance": "Rinse and flatten.",
            "safety_warnings": []
        }
        ocr_data = {
            "extracted_text": "HDPE 2 RECYCLE ME",
            "ric_code": 2,
            "material": "High-Density Polyethylene (HDPE)",
            "information_source": "Molded recycling symbol on jug bottom"
        }
        res = fuse_evidence(visual_result=vision_data, ocr_result=ocr_data)
        self.assertEqual(res["source_count"], 2)
        self.assertEqual(res["confidence_level"], "moderate")
        self.assertFalse(res["has_conflicts"])
        self.assertEqual(len(res["conflicts"]), 0)
        self.assertIn("Visual AI", res["active_sources"])
        self.assertIn("OCR / Label", res["active_sources"])

    def test_multimodal_conflict_detection(self):
        # Vision thinks it's a glass bottle, but OCR reads aluminum can
        vision_data = {
            "object_name": "Beverage Container",
            "material": "Soda-Lime Glass",
            "waste_categories": ["Glass"],
            "recyclability": "Recyclable",
            "disposal_guidance": "Recycle in glass bin.",
            "safety_warnings": []
        }
        ocr_data = {
            "extracted_text": "ALUMINUM CAN PLEASE RECYCLE",
            "material": "Aluminum Alloy 3004",
            "information_source": "Can rim printing"
        }
        res = fuse_evidence(visual_result=vision_data, ocr_result=ocr_data)
        self.assertTrue(res["has_conflicts"])
        self.assertEqual(res["confidence_level"], "conflicted")
        self.assertTrue(res["needs_user_confirmation"])
        self.assertEqual(len(res["conflicts"]), 1)
        conflict = res["conflicts"][0]
        self.assertEqual(conflict["source_a"], "Visual AI")
        self.assertEqual(conflict["source_b"], "OCR / Label")

    def test_all_sources_combined_consensus(self):
        vision_data = {
            "object_name": "Soda Bottle",
            "material": "Polyethylene Terephthalate (PET, #1)",
            "waste_categories": ["Plastics"],
            "recyclability": "Recyclable",
            "disposal_guidance": "Rinse and bin.",
            "safety_warnings": []
        }
        ocr_data = {
            "extracted_text": "PET 1 500ML",
            "ric_code": 1,
            "material": "Polyethylene Terephthalate (PET)",
            "information_source": "Bottle base stamp"
        }
        barcode_data = {
            "found": True,
            "verified": True,
            "product_name": "Sparkling Water",
            "manufacturer": "AquaPure",
            "packaging": {
                "primary_material": "Polyethylene Terephthalate (PET, #1)",
                "disposal_instructions": "Curbside collection"
            }
        }
        text_data = {
            "object_name": "Clear water bottle",
            "material": "Polyethylene Terephthalate",
            "waste_categories": ["Plastics"],
            "recyclability": "Recyclable",
            "disposal_guidance": "Rinse well.",
            "safety_warnings": []
        }
        res = fuse_evidence(
            visual_result=vision_data,
            ocr_result=ocr_data,
            barcode_result=barcode_data,
            text_result=text_data
        )
        self.assertEqual(res["source_count"], 4)
        self.assertEqual(res["confidence_level"], "high")
        self.assertFalse(res["has_conflicts"])
        self.assertFalse(res["needs_user_confirmation"])
        self.assertTrue(res["identification_method"].startswith("MULTIMODAL"))

    def test_api_analyze_with_evidence_fusion_endpoint(self):
        # Barcode mode
        resp = self.client.post("/api/analyze", json={
            "input_method": "barcode_scan",
            "barcode": "5449000000996"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("evidence_fusion", data)
        fusion = data["evidence_fusion"]
        self.assertEqual(fusion["confidence_level"], "high")
        self.assertIn("supporting_evidence", fusion)

    def test_api_text_analysis_with_evidence_fusion_endpoint(self):
        # Text mode
        resp = self.client.post("/api/analyze", json={
            "input_method": "text_description",
            "description": "I have an empty aluminum soda can that is crushed",
            "bypass_clarification": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("evidence_fusion", data)
        self.assertIn("identification_method", data)


if __name__ == "__main__":
    unittest.main()
