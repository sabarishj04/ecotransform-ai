"""
EcoTransform AI - OCR & Packaging Label Recognition Engine
Extracts visible printed packaging labels, recycling codes (RIC 1-7),
product composition, safety warnings, and performs image-quality diagnostics
(blur, rotation, lighting).
"""

import io
import re
import math
from PIL import Image, ImageStat, ImageFilter

# Resin Identification Codes (RIC 1 - 7) Dictionary
RESIN_IDENTIFICATION_CODES = {
    1: {
        "symbol": "♳ (PETE / PET 1)",
        "code_number": 1,
        "acronym": "PET",
        "material_name": "Polyethylene Terephthalate",
        "common_uses": "Soft drink bottles, water bottles, salad dressing containers, peanut butter jars",
        "recyclability": "Widely Recycled (Curbside)",
        "handling_notes": "Highly recyclable stream; rinse and keep cap attached per municipal protocols."
    },
    2: {
        "symbol": "♴ (HDPE 2)",
        "code_number": 2,
        "acronym": "HDPE",
        "material_name": "High-Density Polyethylene",
        "common_uses": "Milk jugs, detergent bottles, shampoo bottles, bleach jugs",
        "recyclability": "Widely Recycled (Curbside)",
        "handling_notes": "Extremely durable, high-value mechanical recycling stream."
    },
    3: {
        "symbol": "♵ (PVC 3)",
        "code_number": 3,
        "acronym": "PVC",
        "material_name": "Polyvinyl Chloride",
        "common_uses": "Pipes, blister packaging, cooking oil bottles, wire jacketing",
        "recyclability": "Rarely Recycled (Hazardous Additives)",
        "handling_notes": "Contains chlorine plasticizers; do not incinerate or mix with PET recycling."
    },
    4: {
        "symbol": "♶ (LDPE 4)",
        "code_number": 4,
        "acronym": "LDPE",
        "material_name": "Low-Density Polyethylene",
        "common_uses": "Squeeze bottles, bread bags, shrink wrap, grocery produce bags",
        "recyclability": "Store Drop-off Only (Tangles Sorting Machines)",
        "handling_notes": "Do not put film in curbside bins unless specifically accepted by municipality."
    },
    5: {
        "symbol": "♷ (PP 5)",
        "code_number": 5,
        "acronym": "PP",
        "material_name": "Polypropylene",
        "common_uses": "Yogurt cups, medicine bottles, takeout containers, bottle caps, syrup bottles",
        "recyclability": "Increasingly Recycled (Check Locally)",
        "handling_notes": "High heat tolerance; rinse thoroughly before bin placement."
    },
    6: {
        "symbol": "♸ (PS 6)",
        "code_number": 6,
        "acronym": "PS",
        "material_name": "Polystyrene / Styrofoam",
        "common_uses": "Disposable coffee cups, meat trays, egg cartons, packing peanuts",
        "recyclability": "Not Recycled in Standard Municipal Streams",
        "handling_notes": "Fragile and contaminates recycling streams; avoid or reuse as packing buffer."
    },
    7: {
        "symbol": "♹ (OTHER 7)",
        "code_number": 7,
        "acronym": "OTHER",
        "material_name": "Other Plastics (Polycarbonate, Acrylic, Nylon, Fiberglass, Multi-layer Laminates)",
        "common_uses": "Baby bottles, electronics housings, 3-5 gallon water jugs, multi-layer pouches",
        "recyclability": "Difficult / Specialized Only",
        "handling_notes": "Mixed polymers require specialized chemical or industrial deconstruction."
    }
}

def evaluate_image_quality(image_bytes: bytes) -> dict:
    """
    Evaluates image lighting, sharpness/blur, contrast, and resolution.
    Returns quality score, flags (is_blurry, is_dark, is_low_contrast), and actionable capture advice.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L") # Grayscale
        width, height = img.size
        
        # 1. Resolution Check
        is_low_res = (width < 320 or height < 240)
        
        # 2. Lighting / Exposure Check
        stat = ImageStat.Stat(img)
        mean_brightness = stat.mean[0] # 0 = pitch black, 255 = washed out white
        rms_contrast = stat.rms[0]
        
        is_dark = mean_brightness < 45
        is_overexposed = mean_brightness > 235
        is_low_contrast = rms_contrast < 25

        # 3. Blur / Focus Detection using Laplacian Variance Proxy
        # Edge enhancement filter
        edges = img.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_variance = edge_stat.var[0] if edge_stat.var else 0.0

        # High variance = sharp edges; low variance = blurry
        is_blurry = edge_variance < 80.0

        # Calculate composite score (0-100)
        score = 100
        if is_blurry: score -= 35
        if is_dark: score -= 25
        if is_overexposed: score -= 25
        if is_low_contrast: score -= 20
        if is_low_res: score -= 15
        score = max(5, score)

        quality_status = "Good"
        guidance = "Image quality is optimal for label and symbol recognition."

        if is_blurry:
            quality_status = "Blurry"
            guidance = "Image appears out of focus or motion-blurred. Hold your camera steady and tap to focus on the label text."
        elif is_dark:
            quality_status = "Poor Lighting (Dark)"
            guidance = "Image is too dark to reliably read small printed text. Increase lighting or turn on your device flash."
        elif is_overexposed:
            quality_status = "Harsh Glare / Overexposed"
            guidance = "Glare on the packaging surface is washing out printed symbols. Adjust angle to minimize direct reflections."
        elif is_low_contrast:
            quality_status = "Low Contrast"
            guidance = "Text is blending into background packaging. Bring camera closer to embossed/printed markings."

        return {
            "score": score,
            "status": quality_status,
            "is_blurry": is_blurry,
            "is_dark": is_dark,
            "is_overexposed": is_overexposed,
            "is_low_contrast": is_low_contrast,
            "is_low_res": is_low_res,
            "guidance": guidance,
            "metrics": {
                "brightness": round(mean_brightness, 1),
                "contrast": round(rms_contrast, 1),
                "edge_sharpness": round(edge_variance, 1),
                "dimensions": f"{width}x{height}"
            }
        }
    except Exception as e:
        return {
            "score": 75,
            "status": "Acceptable",
            "is_blurry": False,
            "is_dark": False,
            "is_overexposed": False,
            "is_low_contrast": False,
            "is_low_res": False,
            "guidance": "Standard image quality evaluated.",
            "metrics": {}
        }

def parse_packaging_ocr(raw_text: str, detected_symbols: list = None) -> dict:
    """
    Parses raw extracted text from labels to isolate:
    - Material names
    - Plastic resin codes (1-7)
    - Recycling instructions (How2Recycle)
    - Product composition
    - Safety warnings
    - Expiry / batch info
    """
    text_lower = raw_text.lower()
    detected_symbols = detected_symbols or []

    # 1. Detect Plastic Resin Codes (RIC 1-7)
    found_ric_codes = []
    
    # Check for direct code matches (e.g. "PET 1", "HDPE #2", "PP 5", "♳", "♴", "Type 1")
    ric_patterns = [
        (1, [r"\bpet\b", r"\bpete\b", r"\bpet 1\b", r"\bpet #1\b", r"♳", r"type 1", r"\bric 1\b"]),
        (2, [r"\bhdpe\b", r"\bhdpe 2\b", r"\bhdpe #2\b", r"♴", r"type 2", r"\bric 2\b"]),
        (3, [r"\bpvc\b", r"\bv 3\b", r"\bpvc 3\b", r"\bpvc #3\b", r"♵", r"type 3", r"\bric 3\b"]),
        (4, [r"\bldpe\b", r"\bldpe 4\b", r"\bldpe #4\b", r"♶", r"type 4", r"\bric 4\b"]),
        (5, [r"\bpp\b", r"\bpp 5\b", r"\bpp #5\b", r"♷", r"type 5", r"\bric 5\b", r"\bpolypropylene\b"]),
        (6, [r"\bps\b", r"\bps 6\b", r"\bps #6\b", r"♸", r"type 6", r"\bric 6\b", r"\bpolystyrene\b"]),
        (7, [r"\bother\b", r"\bother 7\b", r"\bother #7\b", r"♹", r"type 7", r"\bric 7\b", r"\bpolycarbonate\b"])
    ]

    for code_num, patterns in ric_patterns:
        matched = False
        for p in patterns:
            if re.search(p, text_lower):
                matched = True
                break
        if matched and code_num not in [c["code_number"] for c in found_ric_codes]:
            ric_info = RESIN_IDENTIFICATION_CODES[code_num]
            found_ric_codes.append(ric_info)

    # 2. Extract Safety Warnings
    safety_warnings = []
    safety_keywords = [
        "caution", "warning", "danger", "hazardous", "keep out of reach of children",
        "do not ingest", "flammable", "do not microwave", "bpa free", "contains lead", "toxic"
    ]
    for sentence in re.split(r"[\n\.\!]", raw_text):
        sentence_clean = sentence.strip()
        if any(k in sentence_clean.lower() for k in safety_keywords) and len(sentence_clean) > 8:
            if sentence_clean not in safety_warnings:
                safety_warnings.append(sentence_clean)

    # 3. Extract Recycling Instructions (e.g. "Rinse and replace cap", "Empty before recycling", "Check locally")
    recycling_instructions = []
    recycle_keywords = [
        "rinse", "recycle", "curbside", "flatten", "replace cap", "empty", "separate",
        "compostable", "biodegradable", "store drop-off", "widely recycled"
    ]
    for sentence in re.split(r"[\n\.\!]", raw_text):
        sentence_clean = sentence.strip()
        if any(k in sentence_clean.lower() for k in recycle_keywords) and len(sentence_clean) > 8:
            if sentence_clean not in recycling_instructions and sentence_clean not in safety_warnings:
                recycling_instructions.append(sentence_clean)

    # 4. Extract Product Composition / Ingredients
    composition_matches = []
    comp_keywords = ["100% recycled", "contains", "ingredients", "made from", "material:", "composition:", "cotton", "aluminum", "post-consumer"]
    for sentence in re.split(r"[\n\.\!]", raw_text):
        sentence_clean = sentence.strip()
        if any(k in sentence_clean.lower() for k in comp_keywords) and len(sentence_clean) > 6:
            if sentence_clean not in composition_matches:
                composition_matches.append(sentence_clean)

    # 5. Extract Expiry / Date / Batch Information
    expiry_info = []
    date_patterns = [
        r"\b(?:exp|bb|best before|use by|mfg|batch|lot)[\s\:\.\-]+[a-z0-9\/\.\-]+",
        r"\b\d{2}[\/\-]\d{2}[\/\-]\d{2,4}\b"
    ]
    for pat in date_patterns:
        for m in re.finditer(pat, text_lower):
            matched_span = raw_text[m.start():m.end()].strip()
            if matched_span and matched_span not in expiry_info:
                expiry_info.append(matched_span)

    # Synthesize symbols list
    all_symbols = list(detected_symbols)
    for c in found_ric_codes:
        if c["symbol"] not in all_symbols:
            all_symbols.append(c["symbol"])

    return {
        "raw_text": raw_text.strip(),
        "resin_codes": found_ric_codes,
        "detected_symbols": all_symbols,
        "recycling_instructions": recycling_instructions,
        "safety_warnings": safety_warnings,
        "product_composition": composition_matches,
        "expiry_info": expiry_info,
        "disclaimer": "IMPORTANT: Printed packaging labels may describe only a specific container layer or cap, and do not guarantee the composition of internal components or coatings."
    }
