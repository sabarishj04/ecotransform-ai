"""
EcoTransform AI - Automated Pipeline Test Suite
Tests API endpoints, database persistence, and environmental impact calculations.
"""

import unittest
import json
import base64
from app import app
import database as db

class EcoTransformTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        db.init_db()

    def test_health_check(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "healthy")

    def test_analyze_endpoint_with_base64(self):
        # 1x1 transparent PNG in base64
        dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_unit_session_123'},
            json={'image_b64': dummy_b64, 'filename': 'test_bottle.jpg'}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("waste_analysis", data)
        self.assertIn("environmental_impact", data)
        self.assertIn("upcycle_recommendations", data)
        self.assertEqual(len(data["upcycle_recommendations"]), 3)
        self.assertGreater(data["environmental_impact"]["co2_avoided_kg"], 0)

    def test_dashboard_stats(self):
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_scans", data)
        self.assertIn("total_co2_kg", data)
        self.assertIn("material_breakdown", data)

    def test_method_1_camera_input(self):
        dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_cam_session_1'},
            json={
                'input_method': 'camera',
                'image_b64': dummy_b64,
                'filename': 'camera_capture.jpg'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("input_method"), "camera")
        self.assertIn("waste_analysis", data)
        self.assertEqual(len(data["upcycle_recommendations"]), 3)

    def test_method_2_upload_input(self):
        dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_upload_session_2'},
            json={
                'input_method': 'image_upload',
                'image_b64': dummy_b64,
                'filename': 'plastic_bottle.png'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("input_method"), "image_upload")
        self.assertIn("environmental_impact", data)
        self.assertGreater(data["environmental_impact"]["co2_avoided_kg"], 0)

    def test_method_3_text_description(self):
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_text_session_3'},
            json={
                'input_method': 'text_description',
                'description': 'I have a transparent plastic water bottle with a blue cap, approximately 500 ml.'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("input_method"), "text_description")
        self.assertEqual(data.get("identification_method"), "TEXT-BASED AI")
        self.assertIn("Polyethylene", data["waste_analysis"]["primary_material"])
        self.assertIn("Transparent", data["waste_analysis"]["color"])
        self.assertEqual(len(data["upcycle_recommendations"]), 3)

    def test_smart_clarification_trigger_and_resolution(self):
        # 1. Ambiguous query "bottle" should trigger Smart Clarification
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_clarify_session'},
            json={
                'input_method': 'text_description',
                'description': 'bottle'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "needs_clarification")
        self.assertIn("question", data)
        self.assertIn("options", data)
        self.assertIn("plastic, glass, or metal", data["question"])

        # 2. Resubmit with user clarification answer
        res_resolved = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_clarify_session'},
            json={
                'input_method': 'text_description',
                'description': 'bottle',
                'clarification_answer': 'Rigid Plastic'
            }
        )
        self.assertEqual(res_resolved.status_code, 200)
        res_data = res_resolved.get_json()
        self.assertEqual(res_data.get("identification_method"), "TEXT-BASED AI")
        self.assertTrue(any(term in res_data["waste_analysis"]["primary_material"] for term in ["Polyethylene", "PET", "HDPE", "Plastic"]))

    def test_suggested_prompts_coverage(self):
        prompts = [
            ("Old electronic device with lithium battery", "electronic"),
            ("Used clothes worn cotton t-shirt", "textile"),
            ("Food waste organic fruit peelings", "organic"),
            ("Aluminium soda can", "aluminum"),
            ("Glass pickle jar", "glass")
        ]
        for prompt_text, expected_key in prompts:
            res = self.client.post('/api/analyze',
                headers={'X-Session-ID': f'test_prompt_{expected_key}'},
                json={'input_method': 'text_description', 'description': prompt_text}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get("identification_method"), "TEXT-BASED AI")
            self.assertGreater(len(data["upcycle_recommendations"]), 0)

    def test_method_4_manual_selection(self):
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_manual_session_4'},
            json={
                'input_method': 'manual_selection',
                'material_category': 'Aluminum',
                'item_details': 'Crushed 330ml soda can'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("input_method"), "manual_selection")
        self.assertIn("Aluminum", data["waste_analysis"]["primary_material"])
        self.assertEqual(len(data["upcycle_recommendations"]), 3)

    def test_empty_input_validation(self):
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_err_session'},
            json={'input_method': 'text_description', 'description': ''}
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error_code"), "EMPTY_DESCRIPTION")

if __name__ == '__main__':
    unittest.main()
