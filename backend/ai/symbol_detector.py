"""
HVAC/MEP symbol detector using YOLOv8.
Falls back to rule-based detection from vector geometry when model unavailable.
"""
import logging
import os
from pathlib import Path

import numpy as np

from ai.drawing_analyzer import ExtractedGeometry

log = logging.getLogger(__name__)


# Symbol class names per model — Division 23 primary
MECHANICAL_CLASSES = [
    "ahu", "fcu", "vav_box", "diffuser_supply", "diffuser_return",
    "grille", "exhaust_fan", "inline_fan", "pump", "boiler",
    "chiller", "cooling_tower", "heat_exchanger", "vrf_indoor",
    "vrf_outdoor", "split_system", "thermostat", "damper_manual",
    "damper_motorized", "fire_damper", "smoke_damper", "valve_gate",
    "valve_ball", "valve_butterfly", "valve_check", "valve_balancing",
    "coil_heating", "coil_cooling", "filter", "humidifier",
    "expansion_tank", "air_separator", "pressure_gauge", "temperature_sensor",
]

ELECTRICAL_CLASSES = [
    "panel_board", "disconnect", "junction_box", "outlet_120v",
    "outlet_208v", "light_fixture", "exit_sign", "emergency_light",
    "transformer", "vfd", "motor", "starter",
]

PLUMBING_CLASSES = [
    "sink", "toilet", "urinal", "floor_drain", "cleanout",
    "backflow_preventer", "water_heater", "hose_bib",
]


_models: dict[str, object] = {}


def _load_model(model_type: str):
    """Load YOLO model lazily, return None if not available."""
    if model_type in _models:
        return _models[model_type]

    models_path = os.getenv("ML_MODELS_PATH", "./ml_models")
    model_path = Path(models_path) / model_type / "current.pt"

    if not model_path.exists():
        log.warning(f"YOLO model not found at {model_path}, using rule-based fallback")
        _models[model_type] = None
        return None

    try:
        from ultralytics import YOLO
        model = YOLO(str(model_path))
        _models[model_type] = model
        log.info(f"Loaded {model_type} model from {model_path}")
        return model
    except Exception as e:
        log.error(f"Failed to load YOLO model {model_type}: {e}")
        _models[model_type] = None
        return None


async def detect_symbols(drawing_id: int, geom: ExtractedGeometry, file_bytes: bytes) -> list[dict]:
    """
    Detect MEP symbols. Tries YOLO first, falls back to rule-based.
    """
    symbols = []

    # Rule-based detection from block names (DXF) — highest confidence
    rule_symbols = _rule_based_detection(geom)
    symbols.extend(rule_symbols)

    # YOLO detection on rasterized page image
    model = _load_model("mechanical")
    if model is not None:
        yolo_symbols = await _yolo_detect(model, file_bytes, geom, MECHANICAL_CLASSES)
        # Deduplicate against rule-based results
        symbols.extend(_deduplicate(yolo_symbols, rule_symbols))

    return symbols


def _rule_based_detection(geom: ExtractedGeometry) -> list[dict]:
    """
    Detect symbols from DXF block insert names and geometry patterns,
    enriched with structured metadata (tag, model, size, capacity) pulled
    from block ATTRIBs and nearby annotation text.
    """
    from ai.div23.equipment_metadata import extract_metadata, text_within_radius

    symbols = []

    # DXF block names often encode equipment type
    block_name_map = {
        "AHU": "ahu", "FCU": "fcu", "VAV": "vav_box",
        "DIFF": "diffuser_supply", "GRILLE": "grille",
        "EXHAUST": "exhaust_fan", "FAN": "inline_fan",
        "PUMP": "pump", "BOILER": "boiler",
        "CHILLER": "chiller", "TOWER": "cooling_tower",
        "VRF": "vrf_indoor", "TSTAT": "thermostat",
        "DAMPER": "damper_manual", "FD": "fire_damper",
        "SD": "smoke_damper",
    }

    text_elements = geom.text_elements or []

    for block in geom.blocks:
        name_upper = block["name"].upper()
        detected_type = None
        for key, symbol_type in block_name_map.items():
            if key in name_upper:
                detected_type = symbol_type
                break

        if not detected_type:
            continue

        # Look ~6 ft around the symbol for tags/sizes/capacities. Diffusers
        # are densely packed, so use a tighter radius for them.
        radius = 3.0 if detected_type in ("diffuser_supply", "diffuser_return", "grille") else 6.0
        nearby = text_within_radius(block["x"], block["y"], text_elements, radius_ft=radius)
        metadata = extract_metadata(block, nearby_text=nearby)

        properties: dict = {"block_name": block["name"]}
        properties.update(metadata)

        symbols.append({
            "symbol_type": detected_type,
            "x": block["x"],
            "y": block["y"],
            "width": 2.0,
            "height": 2.0,
            "confidence": 0.95,
            "detection_source": "rule",
            "label": metadata.get("tag") or block["name"],
            "properties": properties,
        })

    return symbols


async def _yolo_detect(model, file_bytes: bytes, geom: ExtractedGeometry, classes: list[str]) -> list[dict]:
    """Run YOLOv8 inference on a rasterized page image."""
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.page_count == 0:
            return []
        page = doc[geom.page_number - 1]
        mat = fitz.Matrix(2, 2)  # 2x zoom for better detection
        pix = page.get_pixmap(matrix=mat)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        doc.close()

        conf_threshold = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.45"))
        results = model.predict(img_array, conf=conf_threshold, verbose=False)

        symbols = []
        scale = geom.scale_factor or 96.0
        zoom = 2.0  # we rendered at 2x

        for result in results:
            for box in result.boxes:
                cls_idx = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Convert pixel coords back to feet
                cx_ft = ((x1 + x2) / 2) / zoom / scale
                cy_ft = ((y1 + y2) / 2) / zoom / scale
                w_ft = (x2 - x1) / zoom / scale
                h_ft = (y2 - y1) / zoom / scale

                symbols.append({
                    "symbol_type": classes[cls_idx] if cls_idx < len(classes) else "unknown",
                    "x": cx_ft,
                    "y": cy_ft,
                    "width": w_ft,
                    "height": h_ft,
                    "confidence": conf,
                    "detection_source": "yolo",
                    "label": None,
                    "properties": {"cls_idx": cls_idx},
                })
        return symbols
    except Exception as e:
        log.warning(f"YOLO inference failed: {e}")
        return []


def _deduplicate(new_symbols: list[dict], existing: list[dict], overlap_threshold: float = 1.5) -> list[dict]:
    """Remove YOLO detections that overlap with higher-confidence rule-based detections."""
    unique = []
    for sym in new_symbols:
        overlaps = False
        for ex in existing:
            dist = ((sym["x"] - ex["x"]) ** 2 + (sym["y"] - ex["y"]) ** 2) ** 0.5
            if dist < overlap_threshold:
                overlaps = True
                break
        if not overlaps:
            unique.append(sym)
    return unique
