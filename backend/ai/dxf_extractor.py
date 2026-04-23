"""
DXF/DWG vector geometry extractor using ezdxf.
Handles layer-based material classification.
"""
import io
import math

import ezdxf

from ai.drawing_analyzer import ExtractedGeometry
from ai.layer_classifier import classify_layer_from_name


def extract_dxf(file_bytes: bytes) -> list[ExtractedGeometry]:
    try:
        doc = ezdxf.read(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    except Exception:
        try:
            doc = ezdxf.read(io.BytesIO(file_bytes))
        except Exception:
            return [ExtractedGeometry(page_number=1)]

    geom = ExtractedGeometry(page_number=1)

    # DXF units to feet conversion
    units = doc.header.get("$INSUNITS", 1)  # 1=inches, 4=mm, 6=feet
    unit_to_ft = {1: 1/12, 2: 1/12, 4: 1/304.8, 5: 1/1000, 6: 1.0, 13: 1.0}
    scale = unit_to_ft.get(units, 1/12)
    geom.scale_factor = scale

    # Determine drawing extents
    msp = doc.modelspace()
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for entity in msp:
        layer_name = entity.dxf.layer if entity.dxf.hasattr("layer") else "0"
        material_type = classify_layer_from_name(layer_name)

        if entity.dxftype() == "LINE":
            x1, y1 = entity.dxf.start.x * scale, entity.dxf.start.y * scale
            x2, y2 = entity.dxf.end.x * scale, entity.dxf.end.y * scale
            geom.lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": material_type, "layer_name": layer_name, "linewidth": 1.0, "color": None})
            for x, y in [(x1, y1), (x2, y2)]:
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)

        elif entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            try:
                if entity.dxftype() == "LWPOLYLINE":
                    pts = [{"x": p[0] * scale, "y": p[1] * scale} for p in entity.get_points()]
                else:
                    pts = [{"x": v.dxf.location.x * scale, "y": v.dxf.location.y * scale} for v in entity.vertices]
                if pts:
                    geom.polylines.append({"points": pts, "layer": material_type, "layer_name": layer_name, "closed": entity.is_closed if hasattr(entity, "is_closed") else False, "color": None})
                    for p in pts:
                        min_x, max_x = min(min_x, p["x"]), max(max_x, p["x"])
                        min_y, max_y = min(min_y, p["y"]), max(max_y, p["y"])
            except Exception:
                pass

        elif entity.dxftype() in ("TEXT", "MTEXT"):
            try:
                text = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
                if entity.dxftype() == "TEXT":
                    pos = entity.dxf.insert
                else:
                    pos = entity.dxf.insert
                geom.text_elements.append({
                    "x": pos.x * scale, "y": pos.y * scale,
                    "text": text.replace("\P", "\n").strip(),
                    "rotation": entity.dxf.rotation if entity.dxf.hasattr("rotation") else 0,
                    "height": entity.dxf.height * scale if entity.dxf.hasattr("height") else 0.1,
                    "layer": layer_name,
                })
            except Exception:
                pass

        elif entity.dxftype() == "INSERT":
            try:
                pos = entity.dxf.insert
                geom.blocks.append({
                    "name": entity.dxf.name,
                    "x": pos.x * scale,
                    "y": pos.y * scale,
                    "scale_x": entity.dxf.xscale if entity.dxf.hasattr("xscale") else 1.0,
                    "scale_y": entity.dxf.yscale if entity.dxf.hasattr("yscale") else 1.0,
                    "rotation": entity.dxf.rotation if entity.dxf.hasattr("rotation") else 0,
                    "layer": layer_name,
                })
            except Exception:
                pass

        elif entity.dxftype() == "ARC":
            # Approximate arc as polyline segments
            try:
                cx, cy = entity.dxf.center.x * scale, entity.dxf.center.y * scale
                r = entity.dxf.radius * scale
                a_start = math.radians(entity.dxf.start_angle)
                a_end = math.radians(entity.dxf.end_angle)
                if a_end < a_start:
                    a_end += 2 * math.pi
                steps = max(8, int((a_end - a_start) * r / 0.5))
                pts = []
                for i in range(steps + 1):
                    a = a_start + (a_end - a_start) * i / steps
                    pts.append({"x": cx + r * math.cos(a), "y": cy + r * math.sin(a)})
                geom.polylines.append({"points": pts, "layer": material_type, "layer_name": layer_name, "closed": False, "color": None})
            except Exception:
                pass

    if max_x > min_x and max_y > min_y:
        geom.width_ft = max_x - min_x
        geom.height_ft = max_y - min_y

    return [geom]
