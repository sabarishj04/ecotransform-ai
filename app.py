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
from gemini_service import analyze_waste_image
from impact_calculator import calculate_environmental_impact

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # 6MB limit

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

@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze():
    """
    Core AI Analysis Endpoint:
    Accepts multipart/form-data or JSON (base64 image), performs multimodal vision
    material identification, classifies streams, and generates 3 upcycle recipes.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    session_id = request.headers.get("X-Session-ID") or request.form.get("session_id") or str(uuid.uuid4())
    
    image_bytes = None
    image_preview_b64 = ""
    filename = "upload.jpg"

    # Check multipart file upload
    if "image" in request.files:
        file = request.files["image"]
        if file.filename != "":
            filename = secure_filename(file.filename)
            image_bytes = file.read()
    
    # Or check raw JSON base64 upload
    elif request.is_json and "image_b64" in request.json:
        data = request.json["image_b64"]
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(data)
            filename = request.json.get("filename", "camera_capture.jpg")
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400

    if not image_bytes or len(image_bytes) < 20:
        return jsonify({
            "error_code": "NO_IMAGE_PROVIDED",
            "message": "Please select or capture a waste image to analyze."
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

    # Persist in SQLite database
    saved_record = db.save_scan_result(session_id, analysis_result, image_preview_b64)

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
