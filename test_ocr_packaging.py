"""
Test OCR and Packaging Recognition with the user-provided plastic resin image:
media_1795499908643_f149d213.png
"""

import os
import unittest
import json
from app import app
from ocr_service import evaluate_image_quality, parse_packaging_ocr, RESIN_IDENTIFICATION_CODES
import database as db

USER_IMAGE_PATH = r"C:\Users\sabarish\.gemini\antigravity\brain\e7c9d0cb-4080-43cd-b4e5-a03750b23dbc\.user_uploaded\media_1795499908643_f149d213.png"

class OCRPackagingTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        db.init_db()

    def test_image_quality_evaluation(self):
        self.assertTrue(os.path.exists(USER_IMAGE_PATH), "User uploaded packaging image must exist")
        with open(USER_IMAGE_PATH, "rb") as f:
            img_bytes = f.read()

        quality = evaluate_image_quality(img_bytes)
        self.assertIn("score", quality)
        self.assertIn("status", quality)
        self.assertFalse(quality["is_dark"], "Image is well lit")
        self.assertGreater(quality["score"], 50)
        print(f"\n[Image Quality Diagnostics] Score: {quality['score']}/100, Status: {quality['status']}, Dimensions: {quality['metrics'].get('dimensions')}")

    def test_plastic_identification_codes_1_to_7(self):
        # Verify all 7 plastic codes are represented in resin dictionary
        for code_num in range(1, 8):
            self.assertIn(code_num, RESIN_IDENTIFICATION_CODES)
            info = RESIN_IDENTIFICATION_CODES[code_num]
            self.assertIn("material_name", info)
            self.assertIn("recyclability", info)
            self.assertIn("symbol", info)

        # Test parsing a composite packaging label with codes 1, 2, 4, 5
        sample_label = """
        BOTTLE: 1 PET Widely Recycled
        CAP: 5 PP Check Locally
        SLEEVE: 4 LDPE Store Drop-off
        WARNING: Do not freeze or refill with hot liquids.
        EXP: 2027/12/31
        """
        parsed = parse_packaging_ocr(sample_label)
        ric_nums = [c["code_number"] for c in parsed["resin_codes"]]
        self.assertIn(1, ric_nums)
        self.assertIn(5, ric_nums)
        self.assertIn(4, ric_nums)
        self.assertTrue(len(parsed["safety_warnings"]) > 0)
        self.assertTrue(len(parsed["expiry_info"]) > 0)

    def test_api_analyze_with_real_packaging_image(self):
        with open(USER_IMAGE_PATH, "rb") as f:
            img_bytes = f.read()

        import io
        data = {
            'image': (io.BytesIO(img_bytes), 'plastic_resin_bottles.png'),
            'input_method': 'image_upload'
        }
        res = self.client.post('/api/analyze',
            headers={'X-Session-ID': 'test_ocr_user_img_session'},
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        
        self.assertIn("ocr_evidence", json_data)
        self.assertIn("image_quality", json_data)
        
        ocr = json_data["ocr_evidence"]
        self.assertIn("extracted_text", ocr)
        self.assertIn("detected_symbols", ocr)
        self.assertIn("information_source", ocr)
        self.assertIn("disclaimer", ocr)
        self.assertIn("ocr_confidence", ocr)
        
        print("\n[Real Packaging OCR Extraction Result]:")
        print(f"- Identified Material: {ocr.get('identified_material')}")
        print(f"- Detected Symbols: {ocr.get('detected_symbols')}")
        print(f"- Information Source: {ocr.get('information_source')}")
        print(f"- OCR Confidence: {ocr.get('ocr_confidence') * 100}%")
        print(f"- Quality Status: {json_data['image_quality'].get('status')}")

if __name__ == '__main__':
    unittest.main()
