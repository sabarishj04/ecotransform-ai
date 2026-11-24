"""
EcoTransform AI — Unified Multimodal Waste Intelligence Engine
==============================================================
Fuses evidence from up to 6 input sources:
  1. visual_result     – Gemini Vision analysis of an image
  2. ocr_result        – OCR / packaging label text extracted from image
  3. barcode_result    – Barcode / QR code product lookup
  4. text_result       – Natural-language description analysis (Gemini)
  5. manual_result     – User-selected material category
  6. clarification     – Answers to smart clarification questions

Design principles
-----------------
- Never fabricate confidence numbers or material details.
- Conflict detection: surfaces disagreements between sources honestly.
- Graceful degradation: works with any subset of sources (even just one).
- Secure: no credentials needed here — all AI calls happen in service modules.
- Confidence is expressed as a category, never as a fake percentage.
"""

from __future__ import annotations
import re
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Lower-case, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", str(text or "").lower().strip())


def _first_nonempty(*vals) -> str:
    for v in vals:
        if v:
            s = str(v).strip()
            if s:
                return s
    return ""


def _extract_material_signal(result: dict, source_label: str) -> dict | None:
    """
    Pull the material claim and waste categories from a single-source result dict.
    Returns None if the result is empty or uninformative.
    """
    if not result:
        return None

    material = _first_nonempty(
        result.get("material"),
        result.get("primary_material"),
        result.get("packaging", {}).get("primary_material") if isinstance(result.get("packaging"), dict) else None,
    )
    waste_cats = result.get("waste_categories") or result.get("waste_category") or []
    if isinstance(waste_cats, str):
        waste_cats = [waste_cats]
    object_name = _first_nonempty(
        result.get("object_name"),
        result.get("product_name"),
        result.get("item"),
    )
    recyclability = _first_nonempty(
        result.get("recyclability"),
        result.get("is_recyclable"),
    )
    disposal = _first_nonempty(
        result.get("disposal_guidance"),
        result.get("disposal_instructions"),
        result.get("packaging", {}).get("disposal_instructions") if isinstance(result.get("packaging"), dict) else None,
    )
    safety = result.get("safety_warnings") or []
    if isinstance(safety, str):
        safety = [safety]

    if not (material or object_name):
        return None

    return {
        "source": source_label,
        "object_name": object_name,
        "material": material,
        "waste_categories": waste_cats,
        "recyclability": recyclability,
        "disposal": disposal,
        "safety_warnings": safety,
        "raw": result,
    }


def _materials_conflict(mat_a: str, mat_b: str) -> bool:
    """
    Heuristic: two material strings conflict if they belong to clearly different
    top-level material families. Same family → no conflict even if phrasing differs.
    """
    if not mat_a or not mat_b:
        return False
    if _norm(mat_a) == _norm(mat_b):
        return False

    FAMILIES = {
        "pet":       {"pet", "polyethylene terephthalate"},
        "hdpe":      {"hdpe", "high-density polyethylene"},
        "pvc":       {"pvc", "polyvinyl chloride", "vinyl"},
        "ldpe":      {"ldpe", "low-density polyethylene"},
        "pp":        {"pp", "polypropylene"},
        "ps":        {"ps", "polystyrene"},
        "plastic":   {"plastic", "polymer"},
        "aluminum":  {"aluminum", "aluminium", "al alloy", "alloy 3004"},
        "glass":     {"glass", "soda-lime"},
        "cardboard": {"cardboard", "corrugated", "kraft", "paperboard", "paper"},
        "textile":   {"textile", "fabric", "cotton", "polyester", "nylon", "wool"},
        "electronic":{"electronic", "e-waste", "circuit", "pcb"},
        "organic":   {"organic", "food waste", "compostable", "biodegradable"},
    }

    def family_of(mat: str) -> str | None:
        m = _norm(mat)
        for fam, keywords in FAMILIES.items():
            for kw in keywords:
                if kw in m:
                    return fam
        return None

    fa = family_of(mat_a)
    fb = family_of(mat_b)

    if fa is None or fb is None:
        return False          # Can't determine family → assume no conflict
    if fa == "plastic" or fb == "plastic":
        return False          # Generic "plastic" overlaps every plastic family → not a conflict
    return fa != fb


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fuse_evidence(
    visual_result: dict | None = None,
    ocr_result: dict | None = None,
    barcode_result: dict | None = None,
    text_result: dict | None = None,
    manual_result: dict | None = None,
) -> dict:
    """
    Fuse evidence from all available sources and return a unified structured result.

    Parameters (all optional / may be None)
    ----------------------------------------
    visual_result   : output of gemini_service.analyze_waste_image()
    ocr_result      : output of ocr_service.parse_packaging_ocr() or the
                      ocr_evidence dict already embedded in visual_result
    barcode_result  : output of barcode_service.lookup_barcode_product()
    text_result     : output of gemini_service.analyze_waste_text()
    manual_result   : dict with at least {"material_category": str}

    Returns
    -------
    Unified result dict with keys documented in the architecture spec.
    """

    # -------------------------------------------------------------------
    # 1. Collect evidence signals
    # -------------------------------------------------------------------

    # Pull OCR evidence from visual_result if a separate ocr_result wasn't given
    if ocr_result is None and isinstance(visual_result, dict):
        ocr_result = visual_result.get("ocr_evidence") or None

    # Normalise manual_result into a usable signal dict
    manual_signal_input = None
    if manual_result:
        cat = manual_result.get("material_category") or manual_result.get("material", "")
        details = manual_result.get("item_details", "")
        manual_signal_input = {
            "material": cat,
            "object_name": details or cat,
            "waste_categories": [cat] if cat else [],
        }

    SOURCE_MAP = [
        ("Visual AI",      visual_result),
        ("OCR / Label",    ocr_result),
        ("Barcode / QR",   barcode_result),
        ("Text Analysis",  text_result),
        ("Manual",         manual_signal_input),
    ]

    signals: list[dict] = []
    active_sources: list[str] = []

    for label, raw in SOURCE_MAP:
        sig = _extract_material_signal(raw, label)
        if sig:
            signals.append(sig)
            active_sources.append(label)

    # -------------------------------------------------------------------
    # 2. No signals at all → return an informative error
    # -------------------------------------------------------------------
    if not signals:
        return {
            "error": True,
            "error_code": "NO_EVIDENCE",
            "message": "No identification input was provided. Please supply at least one input (image, text, barcode, or manual selection).",
            "needs_user_confirmation": False,
        }

    # -------------------------------------------------------------------
    # 3. Elect primary result
    # Priority: Visual AI > Text Analysis > OCR / Label > Barcode > Manual
    # -------------------------------------------------------------------
    PRIORITY = ["Visual AI", "Text Analysis", "OCR / Label", "Barcode / QR", "Manual"]

    primary_signal: dict | None = None
    for pref in PRIORITY:
        for sig in signals:
            if sig["source"] == pref:
                primary_signal = sig
                break
        if primary_signal:
            break

    if primary_signal is None:
        primary_signal = signals[0]

    # -------------------------------------------------------------------
    # 4. Conflict detection
    # -------------------------------------------------------------------
    conflicts: list[dict] = []
    reference_material = primary_signal["material"]

    for sig in signals:
        if sig["source"] == primary_signal["source"]:
            continue
        if sig["material"] and _materials_conflict(reference_material, sig["material"]):
            conflicts.append({
                "source_a": primary_signal["source"],
                "material_a": reference_material,
                "source_b": sig["source"],
                "material_b": sig["material"],
                "note": (
                    f"{primary_signal['source']} identified '{reference_material}', "
                    f"but {sig['source']} indicates '{sig['material']}'. "
                    "Please verify by checking labels or markings on the item."
                ),
            })

    # -------------------------------------------------------------------
    # 5. Determine confidence level (qualitative, no fake percentages)
    # -------------------------------------------------------------------
    n_sources = len(signals)

    if conflicts:
        confidence_level = "conflicted"
        confidence_basis = (
            f"{n_sources} source(s) contributed evidence but {len(conflicts)} material conflict(s) were detected. "
            "Review each source below and confirm the correct material."
        )
    elif n_sources >= 3:
        confidence_level = "high"
        confidence_basis = (
            f"{n_sources} independent sources agree on the material identification "
            f"({', '.join(active_sources)})."
        )
    elif n_sources == 2:
        confidence_level = "moderate"
        confidence_basis = (
            f"Two sources agree ({', '.join(active_sources)}). "
            "Additional evidence (image, barcode, or label scan) could strengthen this."
        )
    else:
        # Single source
        source_name = signals[0]["source"]
        if source_name == "Visual AI":
            confidence_level = "moderate"
            confidence_basis = "AI visual analysis only. Scanning a barcode or label could confirm the material."
        elif source_name == "Barcode / QR":
            if barcode_result and barcode_result.get("verified"):
                confidence_level = "high"
                confidence_basis = "Verified barcode match from product registry."
            else:
                confidence_level = "uncertain"
                confidence_basis = "Barcode found but product details could not be verified."
        elif source_name == "Manual":
            confidence_level = "uncertain"
            confidence_basis = "Based on user-selected category only. No AI or sensor analysis performed."
        else:
            confidence_level = "moderate"
            confidence_basis = f"Single source: {source_name}."

    needs_user_confirmation = confidence_level in ("conflicted", "uncertain")

    # -------------------------------------------------------------------
    # 6. Merge disposal guidance and safety warnings across all sources
    # -------------------------------------------------------------------
    disposal_parts: list[str] = []
    safety_set: list[str] = []
    for sig in signals:
        if sig["disposal"] and sig["disposal"] not in disposal_parts:
            disposal_parts.append(sig["disposal"])
        for w in sig["safety_warnings"]:
            if w and w not in safety_set:
                safety_set.append(w)

    merged_disposal = disposal_parts[0] if disposal_parts else "Follow local waste authority guidelines for this material."

    # -------------------------------------------------------------------
    # 7. Build identification_method label
    # -------------------------------------------------------------------
    if len(active_sources) == 1:
        id_method = f"SINGLE SOURCE: {active_sources[0].upper()}"
    else:
        id_method = "MULTIMODAL: " + " + ".join(active_sources)

    # -------------------------------------------------------------------
    # 8. Build supporting_evidence list (one entry per source)
    # -------------------------------------------------------------------
    supporting_evidence: list[dict] = []
    for sig in signals:
        entry: dict[str, Any] = {
            "source": sig["source"],
            "object_name": sig["object_name"],
            "material": sig["material"],
            "waste_categories": sig["waste_categories"],
            "recyclability": sig["recyclability"],
        }
        # Add source-specific extras
        if sig["source"] == "Barcode / QR" and barcode_result:
            entry["product_name"] = barcode_result.get("product_name")
            entry["manufacturer"] = barcode_result.get("manufacturer")
            entry["verified"] = barcode_result.get("verified", False)
        if sig["source"] == "OCR / Label" and ocr_result:
            entry["label_text_snippet"] = (
                (ocr_result.get("extracted_text") or "")[:120] + "…"
                if len(ocr_result.get("extracted_text") or "") > 120
                else ocr_result.get("extracted_text") or ""
            )
            entry["ric_code"] = ocr_result.get("ric_code")
        supporting_evidence.append(entry)

    # -------------------------------------------------------------------
    # 9. Final unified result
    # -------------------------------------------------------------------
    return {
        # Core identification
        "object_name":           _first_nonempty(primary_signal["object_name"], "Waste Item"),
        "material":              primary_signal["material"] or "Unknown",
        "waste_categories":      primary_signal["waste_categories"] or [],
        "identification_method": id_method,

        # Evidence fusion
        "supporting_evidence":   supporting_evidence,
        "active_sources":        active_sources,
        "source_count":          n_sources,

        # Confidence
        "confidence_level":      confidence_level,
        "confidence_basis":      confidence_basis,

        # Conflicts
        "conflicts":             conflicts,
        "has_conflicts":         bool(conflicts),

        # Action
        "needs_user_confirmation": needs_user_confirmation,

        # Disposal
        "recyclability":         primary_signal["recyclability"] or "",
        "disposal_guidance":     merged_disposal,
        "safety_warnings":       safety_set,

        # Pass-through raw primary for downstream rendering
        "primary_source":        primary_signal["source"],
        "primary_raw":           primary_signal["raw"],
    }
