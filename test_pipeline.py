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

if __name__ == '__main__':
    unittest.main()
