"""
Graph-based material run tracer.
Connects line segments of the same material type into continuous runs
and computes real-world lengths in feet.
"""
import math
from collections import defaultdict
from ai.drawing_analyzer import ExtractedGeometry

SNAP_TOLERANCE_FT = 0.5   # endpoints within 0.5 ft are considered connected
PARALLEL_TOLERANCE_FT = 1.0  # parallel lines within 1 ft form a duct pair


def trace_material_runs(geom: ExtractedGeometry) -> list[dict]:
    """
    Returns a list of material run dicts ready for DB insertion.
    """
    runs = []

    # Group all segments (lines and polyline edges) by material type
    segments_by_type: dict[str, list[tuple]] = defaultdict(list)

    for line in geom.lines:
        mat = line.get("layer", "unknown")
        if mat == "unknown":
            continue
        x1, y1, x2, y2 = line["x1"], line["y1"], line["x2"], line["y2"]
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 0.1:  # skip tiny segments
            continue
        segments_by_type[mat].append(((x1, y1), (x2, y2), length, line.get("layer_name", "")))

    for poly in geom.polylines:
        mat = poly.get("layer", "unknown")
        if mat == "unknown":
            continue
        pts = poly["points"]
        for i in range(len(pts) - 1):
            p1 = (pts[i]["x"], pts[i]["y"])
            p2 = (pts[i + 1]["x"], pts[i + 1]["y"])
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if length < 0.1:
                continue
            segments_by_type[mat].append((p1, p2, length, poly.get("layer_name", "")))

    # For each material type, build connected components via union-find
    for mat_type, segments in segments_by_type.items():
        connected = _build_connected_runs(segments)
        for path, total_length, layer_name in connected:
            size = _infer_size_from_layer(layer_name, mat_type)
            runs.append({
                "material_type": mat_type,
                "path": [{"x": p[0], "y": p[1]} for p in path],
                "length_ft": round(total_length, 2),
                "size": size,
                "layer_name": layer_name,
                "confidence": 0.90 if mat_type != "unknown" else 0.50,
                "detection_source": "vector",
            })

    return runs


def _build_connected_runs(segments: list[tuple]) -> list[tuple]:
    """
    Merge line segments that share endpoints (within snap tolerance)
    into continuous paths using a greedy graph traversal.
    """
    # Build adjacency: endpoint → list of (other_endpoint, segment_index)
    adj: dict[tuple, list[tuple]] = defaultdict(list)

    for i, (p1, p2, length, layer) in enumerate(segments):
        adj[_snap(p1)].append((_snap(p2), i))
        adj[_snap(p2)].append((_snap(p1), i))

    visited_segs = set()
    runs = []

    for i, (p1, p2, length, layer) in enumerate(segments):
        if i in visited_segs:
            continue

        # BFS/DFS to collect connected segment chain
        path_points = [p1]
        total_length = 0.0
        stack = [(p1, p2, i)]

        while stack:
            prev, curr_end, seg_idx = stack.pop()
            if seg_idx in visited_segs:
                continue
            visited_segs.add(seg_idx)
            seg = segments[seg_idx]
            total_length += seg[2]
            path_points.append(curr_end)

            # Find connected segments at curr_end
            for neighbor_end, next_seg_idx in adj.get(_snap(curr_end), []):
                if next_seg_idx not in visited_segs:
                    stack.append((curr_end, neighbor_end, next_seg_idx))

        if total_length >= 0.5:  # ignore tiny sub-foot fragments
            runs.append((path_points, total_length, layer))

    return runs


def _snap(point: tuple) -> tuple:
    """Round coordinates to snap tolerance grid."""
    return (
        round(point[0] / SNAP_TOLERANCE_FT) * SNAP_TOLERANCE_FT,
        round(point[1] / SNAP_TOLERANCE_FT) * SNAP_TOLERANCE_FT,
    )


def _infer_size_from_layer(layer_name: str, mat_type: str) -> str | None:
    """
    Try to extract duct/pipe size from layer name.
    Many CAD standards encode size: e.g., DUCT-12x8, PIPE-CHW-4IN
    """
    import re
    upper = layer_name.upper()

    # Duct size: 12x8, 24X12, etc.
    duct_match = re.search(r"(\d+)X(\d+)", upper)
    if duct_match and "DUCT" in mat_type:
        return f"{duct_match.group(1)}x{duct_match.group(2)}"

    # Round duct: 12RD, 8-RD, etc.
    round_match = re.search(r"(\d+)[\s-]?RD", upper)
    if round_match:
        return f"{round_match.group(1)}\" round"

    # Pipe size: 4IN, 4\", 4-INCH
    pipe_match = re.search(r"(\d+(?:\.\d+)?)['\"-]?(?:IN|INCH)?$", upper)
    if pipe_match and "pipe" in mat_type:
        return f"{pipe_match.group(1)}\""

    return None
