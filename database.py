"""
EcoTransform AI - Database Layer
SQLite schema and CRUD operations for scans, material analysis, recommendations, and environmental metrics.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
import os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
DB_PATH = os.path.join(DB_DIR, "ecotransform.db")

def init_db():
    """Initializes and migrates the database schema."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Scans Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        item_name TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        image_preview TEXT,
        created_at TEXT NOT NULL,
        is_deleted INTEGER DEFAULT 0
    )
    """)

    # 2. Material Analysis Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS material_analysis (
        id TEXT PRIMARY KEY,
        scan_id TEXT NOT NULL UNIQUE,
        primary_material TEXT NOT NULL,
        physical_condition TEXT NOT NULL,
        categories_csv TEXT NOT NULL,
        is_hazardous INTEGER DEFAULT 0,
        identification_reasoning TEXT,
        disposal_recommendation TEXT NOT NULL,
        FOREIGN KEY (scan_id) REFERENCES scans (id) ON DELETE CASCADE
    )
    """)

    # 3. Environmental Impact Table (Enhanced with energy, economic value, and user confirmed weight)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS environmental_impact (
        id TEXT PRIMARY KEY,
        scan_id TEXT NOT NULL UNIQUE,
        estimated_weight_kg REAL NOT NULL,
        co2_avoided_kg REAL,
        water_saved_liters REAL,
        energy_saved_kwh REAL,
        landfill_diverted_kg REAL NOT NULL,
        economic_value_inr REAL,
        scenario TEXT DEFAULT 'recycling',
        is_user_confirmed INTEGER DEFAULT 0,
        benchmarking_note TEXT,
        FOREIGN KEY (scan_id) REFERENCES scans (id) ON DELETE CASCADE
    )
    """)

    # Migration: check and add missing columns if upgrading existing DB
    cursor.execute("PRAGMA table_info(environmental_impact)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    if "energy_saved_kwh" not in existing_cols:
        cursor.execute("ALTER TABLE environmental_impact ADD COLUMN energy_saved_kwh REAL")
    if "economic_value_inr" not in existing_cols:
        cursor.execute("ALTER TABLE environmental_impact ADD COLUMN economic_value_inr REAL")
    if "scenario" not in existing_cols:
        cursor.execute("ALTER TABLE environmental_impact ADD COLUMN scenario TEXT DEFAULT 'recycling'")
    if "is_user_confirmed" not in existing_cols:
        cursor.execute("ALTER TABLE environmental_impact ADD COLUMN is_user_confirmed INTEGER DEFAULT 0")

    # 4. Upcycle Recommendations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id TEXT PRIMARY KEY,
        scan_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        estimated_time_mins INTEGER NOT NULL,
        estimated_cost_usd REAL NOT NULL,
        potential_value_usd REAL NOT NULL,
        materials_json TEXT NOT NULL,
        tools_json TEXT NOT NULL,
        steps_json TEXT NOT NULL,
        safety_precautions_json TEXT NOT NULL,
        sustainability_benefit TEXT NOT NULL,
        FOREIGN KEY (scan_id) REFERENCES scans (id) ON DELETE CASCADE
    )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_session ON scans(session_id, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recs_scan ON recommendations(scan_id)")

    conn.commit()
    conn.close()

def get_db_connection():
    """Returns a connection with dictionary row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_scan_result(session_id, scan_data, image_preview=""):
    """Persists a complete analysis result into SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    scan_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    analysis = scan_data.get("waste_analysis", {})
    impact = scan_data.get("environmental_impact", {})
    recs = scan_data.get("upcycle_recommendations", [])

    # 1. Insert Scan
    cursor.execute("""
    INSERT INTO scans (id, session_id, item_name, confidence_score, image_preview, created_at, is_deleted)
    VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        scan_id,
        session_id,
        analysis.get("item_name", "Unknown Waste Item"),
        analysis.get("confidence_score", 0.85),
        image_preview[:50000] if image_preview else "",  # store preview thumbnail
        now_iso
    ))

    # 2. Insert Analysis
    analysis_id = str(uuid.uuid4())
    categories_csv = ",".join(analysis.get("categories", ["Non-recyclable"]))
    cursor.execute("""
    INSERT INTO material_analysis (
        id, scan_id, primary_material, physical_condition,
        categories_csv, is_hazardous, identification_reasoning, disposal_recommendation
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        analysis_id,
        scan_id,
        analysis.get("primary_material", "Composite"),
        analysis.get("physical_condition", "Used"),
        categories_csv,
        1 if analysis.get("is_hazardous") else 0,
        analysis.get("identification_reasoning", ""),
        analysis.get("disposal_recommendation", "Dispose as per municipal rules.")
    ))

    # 3. Insert Environmental Impact
    impact_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO environmental_impact (
        id, scan_id, estimated_weight_kg, co2_avoided_kg,
        water_saved_liters, energy_saved_kwh, landfill_diverted_kg,
        economic_value_inr, scenario, is_user_confirmed, benchmarking_note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        impact_id,
        scan_id,
        impact.get("estimated_weight_kg", 0.05),
        impact.get("co2_avoided_kg"),
        impact.get("water_saved_liters"),
        impact.get("energy_saved_kwh"),
        impact.get("landfill_diverted_kg", 0.05),
        impact.get("economic_value_inr"),
        impact.get("scenario", "recycling"),
        1 if impact.get("is_user_confirmed") else 0,
        impact.get("benchmarking_note", "CPCB & Central Electricity Authority Lifecycle Benchmarks")
    ))

    # 4. Insert Recommendations
    for rec in recs:
        rec_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO recommendations (
            id, scan_id, product_name, difficulty, estimated_time_mins,
            estimated_cost_usd, potential_value_usd, materials_json,
            tools_json, steps_json, safety_precautions_json, sustainability_benefit
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec_id,
            scan_id,
            rec.get("product_name", "Upcycled Project"),
            rec.get("difficulty", "Easy"),
            rec.get("estimated_time_mins", 30),
            rec.get("estimated_cost_usd", 2.0),
            rec.get("potential_value_usd", 15.0),
            json.dumps(rec.get("materials_needed", [])),
            json.dumps(rec.get("tools_needed", [])),
            json.dumps(rec.get("steps", [])),
            json.dumps(rec.get("safety_precautions", [])),
            rec.get("sustainability_benefit", "Prevents landfill waste.")
        ))

    conn.commit()
    conn.close()

    scan_data["scan_id"] = scan_id
    scan_data["created_at"] = now_iso
    scan_data["image_preview"] = image_preview
    return scan_data

def update_scan_weight_and_impact(scan_id: str, new_impact: dict, session_id: str = None) -> bool:
    """Updates the weight, scenario, and environmental metrics for an existing scan."""
    conn = get_db_connection()
    cursor = conn.cursor()

    where_clause = "scan_id = ?"
    params = [
        new_impact.get("estimated_weight_kg", 0.05),
        new_impact.get("co2_avoided_kg"),
        new_impact.get("water_saved_liters"),
        new_impact.get("energy_saved_kwh"),
        new_impact.get("landfill_diverted_kg", 0.05),
        new_impact.get("economic_value_inr"),
        new_impact.get("scenario", "recycling"),
        1 if new_impact.get("is_user_confirmed") else 0,
        new_impact.get("benchmarking_note", ""),
        scan_id
    ]

    cursor.execute("""
    UPDATE environmental_impact
    SET estimated_weight_kg = ?,
        co2_avoided_kg = ?,
        water_saved_liters = ?,
        energy_saved_kwh = ?,
        landfill_diverted_kg = ?,
        economic_value_inr = ?,
        scenario = ?,
        is_user_confirmed = ?,
        benchmarking_note = ?
    WHERE scan_id = ?
    """, params)

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_scan_history(session_id=None, limit=20):
    """Retrieves recent scans filtered by session or global."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT s.id, s.item_name, s.confidence_score, s.image_preview, s.created_at,
           m.primary_material, m.categories_csv,
           e.estimated_weight_kg, e.co2_avoided_kg, e.water_saved_liters, e.energy_saved_kwh,
           e.landfill_diverted_kg, e.economic_value_inr, e.scenario, e.is_user_confirmed
    FROM scans s
    LEFT JOIN material_analysis m ON s.id = m.scan_id
    LEFT JOIN environmental_impact e ON s.id = e.scan_id
    WHERE s.is_deleted = 0
    """
    params = []
    if session_id:
        query += " AND s.session_id = ?"
        params.append(session_id)

    query += " ORDER BY s.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "item_name": r["item_name"],
            "confidence_score": r["confidence_score"],
            "image_preview": r["image_preview"],
            "created_at": r["created_at"],
            "primary_material": r["primary_material"],
            "categories": r["categories_csv"].split(",") if r["categories_csv"] else [],
            "impact": {
                "estimated_weight_kg": r["estimated_weight_kg"],
                "co2_avoided_kg": r["co2_avoided_kg"],
                "water_saved_liters": r["water_saved_liters"],
                "energy_saved_kwh": r["energy_saved_kwh"],
                "landfill_diverted_kg": r["landfill_diverted_kg"],
                "economic_value_inr": r["economic_value_inr"],
                "scenario": r["scenario"],
                "is_user_confirmed": bool(r["is_user_confirmed"])
            }
        })
    return history

def get_scan_detail(scan_id):
    """Returns complete details of a specific scan."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.id, s.session_id, s.item_name, s.confidence_score, s.image_preview, s.created_at,
           m.primary_material, m.physical_condition, m.categories_csv, m.is_hazardous,
           m.identification_reasoning, m.disposal_recommendation,
           e.estimated_weight_kg, e.co2_avoided_kg, e.water_saved_liters, e.energy_saved_kwh,
           e.landfill_diverted_kg, e.economic_value_inr, e.scenario, e.is_user_confirmed, e.benchmarking_note
    FROM scans s
    LEFT JOIN material_analysis m ON s.id = m.scan_id
    LEFT JOIN environmental_impact e ON s.id = e.scan_id
    WHERE s.id = ? AND s.is_deleted = 0
    """, (scan_id,))

    r = cursor.fetchone()
    if not r:
        conn.close()
        return None

    # Recommendations
    cursor.execute("""
    SELECT id, product_name, difficulty, estimated_time_mins, estimated_cost_usd,
           potential_value_usd, materials_json, tools_json, steps_json,
           safety_precautions_json, sustainability_benefit
    FROM recommendations
    WHERE scan_id = ?
    """, (scan_id,))

    rec_rows = cursor.fetchall()
    recs = []
    for rec in rec_rows:
        recs.append({
            "id": rec["id"],
            "product_name": rec["product_name"],
            "difficulty": rec["difficulty"],
            "estimated_time_mins": rec["estimated_time_mins"],
            "estimated_cost_usd": rec["estimated_cost_usd"],
            "potential_value_usd": rec["potential_value_usd"],
            "materials_needed": json.loads(rec["materials_json"]),
            "tools_needed": json.loads(rec["tools_json"]),
            "steps": json.loads(rec["steps_json"]),
            "safety_precautions": json.loads(rec["safety_precautions_json"]),
            "sustainability_benefit": rec["sustainability_benefit"]
        })

    conn.close()

    return {
        "scan_id": r["id"],
        "created_at": r["created_at"],
        "image_preview": r["image_preview"],
        "waste_analysis": {
            "item_name": r["item_name"],
            "primary_material": r["primary_material"],
            "physical_condition": r["physical_condition"],
            "confidence_score": r["confidence_score"],
            "categories": r["categories_csv"].split(",") if r["categories_csv"] else [],
            "is_hazardous": bool(r["is_hazardous"]),
            "identification_reasoning": r["identification_reasoning"],
            "disposal_recommendation": r["disposal_recommendation"]
        },
        "environmental_impact": {
            "estimated_weight_kg": r["estimated_weight_kg"],
            "co2_avoided_kg": r["co2_avoided_kg"],
            "water_saved_liters": r["water_saved_liters"],
            "energy_saved_kwh": r["energy_saved_kwh"],
            "landfill_diverted_kg": r["landfill_diverted_kg"],
            "economic_value_inr": r["economic_value_inr"],
            "scenario": r["scenario"] or "recycling",
            "is_user_confirmed": bool(r["is_user_confirmed"]),
            "benchmarking_note": r["benchmarking_note"]
        },
        "upcycle_recommendations": recs
    }

def delete_scan(scan_id, session_id):
    """Soft deletes a scan for a specific session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE scans SET is_deleted = 1 WHERE id = ? AND session_id = ?
    """, (scan_id, session_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_dashboard_stats(session_id=None):
    """Computes aggregate sustainability metrics across all scans or a user's session."""
    conn = get_db_connection()
    cursor = conn.cursor()

    where_clause = "WHERE s.is_deleted = 0"
    params = []
    if session_id:
        where_clause += " AND s.session_id = ?"
        params.append(session_id)

    # Aggregates
    cursor.execute(f"""
    SELECT 
        COUNT(s.id) as total_scans,
        COALESCE(SUM(e.landfill_diverted_kg), 0) as total_landfill_kg,
        COALESCE(SUM(e.co2_avoided_kg), 0) as total_co2_kg,
        COALESCE(SUM(e.water_saved_liters), 0) as total_water_liters,
        COALESCE(SUM(e.energy_saved_kwh), 0) as total_energy_kwh,
        COALESCE(SUM(e.economic_value_inr), 0) as total_economic_inr
    FROM scans s
    LEFT JOIN environmental_impact e ON s.id = e.scan_id
    {where_clause}
    """, params)
    agg = cursor.fetchone()

    # Material breakdown
    cursor.execute(f"""
    SELECT m.primary_material, COUNT(*) as count
    FROM material_analysis m
    JOIN scans s ON m.scan_id = s.id
    {where_clause}
    GROUP BY m.primary_material
    ORDER BY count DESC
    LIMIT 6
    """, params)
    mat_rows = cursor.fetchall()
    material_breakdown = [{"material": r["primary_material"], "count": r["count"]} for r in mat_rows]

    # Total Upcycling Recommendations generated
    cursor.execute(f"""
    SELECT COUNT(r.id) as total_blueprints
    FROM recommendations r
    JOIN scans s ON r.scan_id = s.id
    {where_clause}
    """, params)
    bp_row = cursor.fetchone()

    conn.close()

    total_scans = agg["total_scans"] or 0
    total_landfill_kg = round(agg["total_landfill_kg"] or 0.0, 3)
    total_weight_kg = total_landfill_kg  # Material weight diverted from waste stream

    return {
        "total_scans": total_scans,
        "total_waste_identified": total_scans,
        "total_material_weight_kg": total_weight_kg,
        "total_material_weight_g": round(total_weight_kg * 1000.0, 1),
        "total_landfill_kg": total_landfill_kg,
        "total_co2_kg": round(agg["total_co2_kg"] or 0.0, 3),
        "total_water_liters": round(agg["total_water_liters"] or 0.0, 1),
        "total_energy_kwh": round(agg["total_energy_kwh"] or 0.0, 2),
        "total_economic_inr": round(agg["total_economic_inr"] or 0.0, 2),
        "total_blueprints": bp_row["total_blueprints"] if bp_row else (total_scans * 3),
        "material_breakdown": material_breakdown,
        "is_empty": (total_scans == 0)
    }
