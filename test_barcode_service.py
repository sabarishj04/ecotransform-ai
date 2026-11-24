"""
EcoTransform AI - Barcode & QR Code Automated Test Suite
Verifies:
1. Lookup of common barcodes (EAN-13, UPC, Code-128).
2. Packaging material composition retrieval.
3. Accurate handling of unmatched barcodes without inventing details.
4. Manual correction workflow.
5. Integration into the unified /api/analyze endpoint.
"""

import unittest
from app import app
from barcode_service import lookup_barcode_product, VERIFIED_PRODUCT_CATALOG
import database as db

class BarcodeServiceTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        db.init_db()

    def test_verified_barcode_lookup(self):
        # 1. Coca-Cola 500ml PET
        result = lookup_barcode_product("5449000000996")
        self.assertTrue(result["found"])
        self.assertTrue(result["verified"])
        self.assertIn("Coca-Cola", result["product_name"])
        self.assertIn("The Coca-Cola Company", result["brand_owner"])
        self.assertEqual(result["packaging"]["primary_material"], "Polyethylene Terephthalate (PET, #1)")

        # 2. Pepsi 330ml Aluminum Can
        pepsi = lookup_barcode_product("4060800000304")
        self.assertTrue(pepsi["found"])
        self.assertEqual(pepsi["packaging"]["primary_material"], "Aluminum Alloy 3004")

        # 3. Duracell AA Battery Pack
        duracell = lookup_barcode_product("5000394002975")
        self.assertTrue(duracell["found"])
        self.assertIn("Alkaline", duracell["packaging"]["primary_material"])

    def test_unverified_barcode_does_not_invent_data(self):
        unverified_code = "9999999999999"
        result = lookup_barcode_product(unverified_code)
        self.assertFalse(result["found"])
        self.assertFalse(result["verified"])
        self.assertNotIn("packaging", result)
        self.assertIn("No verified product match found", result["message"])

    def test_qr_code_url_handling(self):
        qr_url = "https://recycling.org/packaging/info?id=123"
        result = lookup_barcode_product(qr_url)
        self.assertTrue(result["found"])
        self.assertEqual(result["barcode_type"], "QR-Code URL")

    def test_api_barcode_lookup_endpoint(self):
        res = self.client.post('/api/barcode/lookup', json={'barcode': '5449000000996'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["product_name"], "Coca-Cola Original Taste (500ml)")

    def test_unified_analyze_with_barcode(self):
        # Scan verified barcode and assert it flows through EPA lifecycle & blueprints
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_barcode_session_1'},
            json={
                'input_method': 'barcode_scan',
                'barcode': '5449000000996'
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("identification_method"), "VERIFIED BARCODE / QR")
        self.assertIn("barcode_evidence", data)
        self.assertTrue(data["barcode_evidence"]["verified"])
        self.assertGreater(data["environmental_impact"]["co2_avoided_kg"], 0)
        self.assertEqual(len(data["upcycle_recommendations"]), 3)

    def test_unified_analyze_with_manual_correction(self):
        # User submits unverified barcode + manual correction
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_correction_session_2'},
            json={
                'input_method': 'barcode_scan',
                'barcode': '1234567890123',
                'manual_correction': {
                    'product_name': 'Craft Organic Cold Brew (Glass Bottle)',
                    'material': 'Soda-Lime Silica Glass',
                    'notes': 'Metal crown cap'
                }
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("identification_method"), "VERIFIED BARCODE / QR")
        self.assertTrue(data["barcode_evidence"]["manual_correction_applied"])
        self.assertIn("Glass", data["waste_analysis"]["primary_material"])

if __name__ == '__main__':
    unittest.main()
