"""
EcoTransform AI - Flask Application & REST API Service
Serves the web application and RESTful endpoints for waste identification,
classification, waste-to-wealth blueprints, and sustainability analytics.
"""

import os
import base64
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import io

import database as db
from gemini_service import analyze_waste_image, analyze_waste_text, check_text_clarification_needed
from impact_calculator import calculate_environmental_impact
from barcode_service import lookup_barcode_product, VERIFIED_PRODUCT_CATALOG
from intelligence_engine import fuse_evidence
from centers_service import search_recycling_centres, VERIFIED_RECYCLING_CENTRES

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB limit

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize SQLite database on startup
db.init_db()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-ID"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response

@app.route("/")
def index():
    """Serves the main application SPA."""
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health_check():
    """Service health and readiness check."""
    return jsonify({
        "status": "healthy",
        "service": "EcoTransform AI",
        "version": "1.0.0",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY"))
    })

@app.route("/api/barcode/lookup", methods=["POST", "OPTIONS"])
def barcode_lookup():
    """
    Looks up Barcode (EAN-13, UPC, Code-128) or QR code in verified product registry.
    Returns manufacturer, verified product name, material composition, and packaging stream.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    barcode_code = str(data.get("barcode", "")).strip()

    if not barcode_code:
        return jsonify({
            "error_code": "EMPTY_BARCODE",
            "message": "Please provide a barcode or QR code number."
        }), 400

    result = lookup_barcode_product(barcode_code)
    return jsonify(result), 200

@app.route("/api/barcode/samples", methods=["GET"])
def barcode_samples():
    """Returns verified sample barcodes for 1-click evaluation."""
    samples = []
    for code, item in VERIFIED_PRODUCT_CATALOG.items():
        samples.append({
            "barcode": code,
            "product_name": item["product_name"],
            "barcode_type": item["barcode_type"],
            "manufacturer": item["manufacturer"],
            "material": item["packaging"]["primary_material"]
        })
    return jsonify({"samples": samples}), 200

@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze():
    """
    Core AI Analysis Endpoint:
    Accepts 4 identification methods:
    1. Camera (base64 image or multipart)
    2. Image Upload (multipart file or base64)
    3. Text Description (natural language)
    4. Manual Selection (known waste category + optional condition)
    
    Routes through live Gemini model or robust offline materials engine,
    calculates EPA lifecycle impacts, and stores in database.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    session_id = request.headers.get("X-Session-ID") or request.form.get("session_id") or str(uuid.uuid4())
    
    image_bytes = None
    image_preview_b64 = ""
    filename = "upload.jpg"
    input_method = "image_upload"

    # 1 & 2: Check multipart file upload
    if "image" in request.files:
        file = request.files["image"]
        if file.filename != "":
            filename = secure_filename(file.filename)
            image_bytes = file.read()
            input_method = request.form.get("input_method", "image_upload")
    
    # Check JSON body (Base64 image, text description, or manual category selection)
    elif request.is_json:
        data = request.json
        input_method = data.get("input_method", "image_upload")
        scanned_barcode = data.get("barcode", "").strip()
        manual_correction = data.get("manual_correction")
        
        # Method 1 & 2: Base64 image
        if "image_b64" in data and data["image_b64"]:
            raw_b64 = data["image_b64"]
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            try:
                image_bytes = base64.b64decode(raw_b64)
                filename = data.get("filename", "camera_capture.jpg" if input_method == "camera" else "upload.jpg")
            except Exception:
                return jsonify({"error": "Invalid base64 image data"}), 400

        # Method: Direct Barcode / QR Code identification
        elif input_method == "barcode_scan" or scanned_barcode:
            barcode_res = lookup_barcode_product(scanned_barcode)

            # If manual correction provided by user
            if manual_correction:
                product_name = manual_correction.get("product_name") or barcode_res.get("product_name") or f"Product #{scanned_barcode}"
                primary_material = manual_correction.get("material") or "Recyclable Polymer Composite"
            elif barcode_res.get("found") and barcode_res.get("verified"):
                product_name = barcode_res["product_name"]
                primary_material = barcode_res["packaging"]["primary_material"]
            else:
                product_name = f"Unregistered Product #{scanned_barcode}"
                primary_material = "Unknown Packaging Polymer"

            analysis_result = analyze_waste_text(
                description=product_name,
                material_hint=primary_material
            )
            barcode_evidence = {
                "barcode": scanned_barcode,
                "found": barcode_res.get("found", False),
                "verified": barcode_res.get("verified", False),
                "product_name": barcode_res.get("product_name"),
                "brand_owner": barcode_res.get("brand_owner"),
                "manufacturer": barcode_res.get("manufacturer"),
                "barcode_type": barcode_res.get("barcode_type"),
                "source": barcode_res.get("source"),
                "message": barcode_res.get("message"),
                "packaging": barcode_res.get("packaging"),
                "manual_correction_applied": bool(manual_correction)
            }
            analysis_result["barcode_evidence"] = barcode_evidence

            # Fuse evidence through intelligence engine
            fusion = fuse_evidence(
                barcode_result=barcode_res,
                text_result=analysis_result if manual_correction else None,
            )

            id_method = "VERIFIED BARCODE / QR" if (barcode_res.get("verified") or manual_correction) else fusion.get("identification_method", "BARCODE / QR")
            analysis_result["identification_method"] = id_method
            saved_record = db.save_scan_result(session_id, analysis_result, image_preview="")
            saved_record["input_method"] = "barcode_scan"
            saved_record["identification_method"] = id_method
            saved_record["barcode_evidence"] = barcode_evidence
            saved_record["evidence_fusion"] = fusion
            return jsonify(saved_record), 200

        # Method 3: Text Description
        elif input_method == "text_description" or ("description" in data and not image_bytes):
            description = data.get("description", "").strip()
            material_hint = data.get("material_category", "").strip()
            clarification_answer = data.get("clarification_answer", "").strip()
            bypass_clarification = data.get("bypass_clarification", False)

            if not description:
                return jsonify({
                    "error_code": "EMPTY_DESCRIPTION",
                    "message": "Please enter a description of the waste item."
                }), 400

            # Smart Clarification Engine
            if not bypass_clarification and not clarification_answer:
                clarification = check_text_clarification_needed(description)
                if clarification.get("needs_clarification"):
                    return jsonify({
                        "status": "needs_clarification",
                        "question": clarification["question"],
                        "options": clarification["options"],
                        "clarification_key": clarification["clarification_key"],
                        "original_description": description
                    }), 200

            analysis_result = analyze_waste_text(
                description,
                material_hint=material_hint,
                clarification_answer=clarification_answer
            )

            manual_sig = {"material_category": material_hint} if material_hint else None
            fusion = fuse_evidence(text_result=analysis_result, manual_result=manual_sig)

            saved_record = db.save_scan_result(session_id, analysis_result, image_preview="")
            saved_record["input_method"] = "text_description"
            saved_record["identification_method"] = fusion.get("identification_method", "TEXT-BASED AI")
            saved_record["evidence_fusion"] = fusion
            return jsonify(saved_record), 200

        # Method 4: Manual Material Selection
        elif input_method == "manual_selection" or ("material_category" in data and not image_bytes):
            material_category = data.get("material_category", "").strip()
            item_details = data.get("item_details", "").strip()
            if not material_category:
                return jsonify({
                    "error_code": "EMPTY_CATEGORY",
                    "message": "Please select a material category from the list."
                }), 400

            desc = f"{item_details} ({material_category})" if item_details else material_category
            analysis_result = analyze_waste_text(desc, material_hint=material_category)
            manual_sig = {"material_category": material_category, "item_details": item_details}
            fusion = fuse_evidence(text_result=analysis_result, manual_result=manual_sig)

            saved_record = db.save_scan_result(session_id, analysis_result, image_preview="")
            saved_record["input_method"] = "manual_selection"
            saved_record["identification_method"] = fusion.get("identification_method", "MANUAL SELECTION")
            saved_record["evidence_fusion"] = fusion
            return jsonify(saved_record), 200

    # Also check if text / manual came through form-data
    if not image_bytes:
        form_method = request.form.get("input_method")
        if form_method == "text_description" and request.form.get("description"):
            desc = request.form.get("description").strip()
            hint = request.form.get("material_category", "").strip()
            analysis_result = analyze_waste_text(desc, material_hint=hint)
            saved_record = db.save_scan_result(session_id, analysis_result, image_preview="")
            saved_record["input_method"] = "text_description"
            return jsonify(saved_record), 200
        elif form_method == "manual_selection" and request.form.get("material_category"):
            category = request.form.get("material_category").strip()
            details = request.form.get("item_details", "").strip()
            desc = f"{details} ({category})" if details else category
            analysis_result = analyze_waste_text(desc, material_hint=category)
            saved_record = db.save_scan_result(session_id, analysis_result, image_preview="")
            saved_record["input_method"] = "manual_selection"
            return jsonify(saved_record), 200

        return jsonify({
            "error_code": "NO_INPUT_PROVIDED",
            "message": "Please capture an image, upload a file, describe the item, or select a category."
        }), 400

    # Process and compress image thumbnail for quick preview in history
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((300, 300))
        thumb_io = io.BytesIO()
        img.convert("RGB").save(thumb_io, format="JPEG", quality=70)
        image_preview_b64 = "data:image/jpeg;base64," + base64.b64encode(thumb_io.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Thumbnail generation skipped: {e}")
        image_preview_b64 = ""

    # Execute Multimodal AI Analysis
    analysis_result = analyze_waste_image(image_bytes, filename=filename)

    # Fuse evidence across Visual AI and embedded OCR
    ocr_evidence = analysis_result.get("ocr_evidence")
    fusion = fuse_evidence(
        visual_result=analysis_result,
        ocr_result=ocr_evidence
    )
    analysis_result["evidence_fusion"] = fusion

    # Persist in SQLite database
    saved_record = db.save_scan_result(session_id, analysis_result, image_preview_b64)
    saved_record["input_method"] = input_method
    saved_record["evidence_fusion"] = fusion

    return jsonify(saved_record), 200

@app.route("/api/history", methods=["GET"])
def history():
    """Returns past scans for the current session."""
    session_id = request.headers.get("X-Session-ID") or request.args.get("session_id", "")
    limit = int(request.args.get("limit", 20))
    scans = db.get_scan_history(session_id, limit=limit)
    return jsonify({"scans": scans})

@app.route("/api/history/<scan_id>", methods=["GET"])
def get_scan(scan_id):
    """Returns deep details and recipes for a specific past scan."""
    detail = db.get_scan_detail(scan_id)
    if not detail:
        return jsonify({"error": "Scan record not found"}), 404
    return jsonify(detail)

@app.route("/api/history/<scan_id>", methods=["DELETE"])
def delete_scan_record(scan_id):
    """Soft deletes a scan record."""
    session_id = request.headers.get("X-Session-ID", "")
    success = db.delete_scan(scan_id, session_id)
    if not success:
        return jsonify({"error": "Unable to delete scan record"}), 400
    return jsonify({"success": True, "message": "Scan deleted successfully"})

@app.route("/api/impact/recalculate", methods=["POST", "OPTIONS"])
def recalculate_impact():
    """
    Recalculates environmental & economic impact when user edits weight or switches scenario.
    Optionally persists confirmed weight and updated metrics to database if scan_id provided.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    item_name = data.get("item_name", "Waste Item")
    primary_material = data.get("primary_material", "Plastic")
    raw_weight = data.get("weight")
    unit = str(data.get("unit", "kg")).lower().strip()
    scenario = str(data.get("scenario", "recycling")).lower().strip()
    is_user_confirmed = bool(data.get("is_user_confirmed", True))
    scan_id = data.get("scan_id")

    # Validate weight input
    try:
        weight_val = float(raw_weight)
        if weight_val <= 0:
            return jsonify({
                "error_code": "INVALID_WEIGHT",
                "message": "Weight must be greater than zero."
            }), 400
        
        # Convert grams to kilograms if specified
        weight_kg = weight_val / 1000.0 if unit == "g" else weight_val
    except (TypeError, ValueError):
        return jsonify({
            "error_code": "INVALID_WEIGHT_FORMAT",
            "message": "Please enter a valid numeric weight."
        }), 400

    # Calculate updated metrics
    impact = calculate_environmental_impact(
        item_name=item_name,
        primary_material=primary_material,
        detected_weight_kg=weight_kg,
        scenario=scenario,
        is_user_confirmed=is_user_confirmed,
        unit=unit
    )

    # Persist in database if scan_id is provided
    if scan_id:
        db.update_scan_weight_and_impact(scan_id, impact)

    return jsonify(impact), 200

@app.route("/api/centres", methods=["GET"])
def recycling_centres():
    """
    Returns verified municipal and authorized recycling & material recovery centres.
    Supports filtering by city (e.g. Chennai, Bengaluru, Mumbai), stream, and query.
    """
    city = request.args.get("city", "")
    stream = request.args.get("stream", "")
    q = request.args.get("q", "")
    centres = search_recycling_centres(city=city, stream=stream, query=q)
    return jsonify({
        "total": len(centres),
        "centres": centres,
        "supported_cities": ["Chennai", "Coimbatore", "Madurai", "Bengaluru", "Mumbai", "New Delhi", "Hyderabad"]
    }), 200

@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Returns aggregate sustainability metrics across all scans."""
    session_id = request.headers.get("X-Session-ID") or request.args.get("session_id")
    # If session provided, returns personal stats; otherwise platform global stats
    scope = request.args.get("scope", "global")
    stats = db.get_dashboard_stats(session_id if scope == "personal" else None)
    return jsonify(stats)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌱 EcoTransform AI running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
