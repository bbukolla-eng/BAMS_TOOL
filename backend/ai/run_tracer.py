"""
Graph-based material run tracer.
Connects line segments of the same material type into continuous runs,
computes real-world lengths in feet, and counts in-line fittings (elbows,
tees, transitions) from the connectivity graph.
"""
import math
from collections import defaultdict

from ai.drawing_analyzer import ExtractedGeometry

SNAP_TOLERANCE_FT = 0.5   # endpoints within 0.5 ft are considered connected
PARALLEL_TOLERANCE_FT = 1.0  # parallel lines within 1 ft form a duct pair

# A bend smaller than this is treated as drafting noise; a bend larger than
# this counts as an elbow. 30° matches the smallest practical HVAC fitting.
ELBOW_MIN_ANGLE_DEG = 30.0
# Bends >= 75° are 90° elbows; otherwise 45° elbows.
ELBOW_45_THRESHOLD_DEG = 75.0


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
        for path, total_length, layer_name, fittings in connected:
            size = _infer_size_from_layer(layer_name, mat_type)
            runs.append({
                "material_type": mat_type,
                "path": [{"x": p[0], "y": p[1]} for p in path],
                "length_ft": round(total_length, 2),
                "size": size,
                "layer_name": layer_name,
                "confidence": 0.90 if mat_type != "unknown" else 0.50,
                "detection_source": "vector",
                "fittings": fittings,
            })

    return runs


def _build_connected_runs(segments: list[tuple]) -> list[tuple]:
    """
    Merge line segments that share endpoints (within snap tolerance)
    into continuous paths using a greedy graph traversal. For each connected
    component, also classify vertices into HVAC fittings:

    - degree 1  → end (cap or tap; ignored in the fitting count)
    - degree 2  → straight (no fitting) OR elbow (45°/90°) if angle bends
    - degree 3  → tee
    - degree ≥4 → cross / wye (counted as 'tee' since cross is rare)
    Plus 'transition' wherever neighboring segments encode different sizes
    in their layer name.

    Returns: list of (path_points, total_length, layer_name, fittings_dict)
    """
    # Build adjacency: endpoint → list of (other_endpoint, segment_index)
    adj: dict[tuple, list[tuple]] = defaultdict(list)

    for i, (p1, p2, _length, _layer) in enumerate(segments):
        adj[_snap(p1)].append((_snap(p2), i))
        adj[_snap(p2)].append((_snap(p1), i))

    visited_segs: set[int] = set()
    runs = []

    for i in range(len(segments)):
        if i in visited_segs:
            continue

        # BFS to collect every segment in this connected component.
        component_seg_ids: list[int] = []
        component_endpoints: set[tuple] = set()
        total_length = 0.0
        layer = segments[i][3]

        stack = [i]
        while stack:
            seg_idx = stack.pop()
            if seg_idx in visited_segs:
                continue
            visited_segs.add(seg_idx)
            component_seg_ids.append(seg_idx)
            p1, p2, length, _ = segments[seg_idx]
            total_length += length
            component_endpoints.add(_snap(p1))
            component_endpoints.add(_snap(p2))
            for endpoint in (_snap(p1), _snap(p2)):
                for _, next_seg_idx in adj.get(endpoint, []):
                    if next_seg_idx not in visited_segs:
                        stack.append(next_seg_idx)

        if total_length < 0.5 or not component_seg_ids:
            continue

        path_points = _path_through(component_seg_ids, segments, adj)
        fittings = _count_fittings(component_endpoints, component_seg_ids, segments, adj)
        runs.append((path_points, total_length, layer, fittings))

    return runs


def _path_through(seg_ids: list[int], segments: list[tuple], adj: dict) -> list[tuple]:
    """Best-effort ordered path. Starts from a degree-1 endpoint when present
    (so the path reads cleanly from one end to the other), otherwise from any
    endpoint of the first segment. Used only for visualization, not totals."""
    seg_set = set(seg_ids)
    endpoint_degrees: dict[tuple, int] = defaultdict(int)
    for sid in seg_ids:
        p1, p2, _, _ = segments[sid]
        endpoint_degrees[_snap(p1)] += 1
        endpoint_degrees[_snap(p2)] += 1
    start: tuple | None = None
    for endpoint, degree in endpoint_degrees.items():
        if degree == 1:
            start = endpoint
            break
    if start is None:
        p1, _, _, _ = segments[seg_ids[0]]
        start = _snap(p1)

    path = [start]
    visited_local: set[int] = set()
    current = start
    while True:
        next_step = None
        for neighbour, sid in adj.get(current, []):
            if sid in seg_set and sid not in visited_local:
                next_step = (neighbour, sid)
                break
        if not next_step:
            break
        neighbour, sid = next_step
        visited_local.add(sid)
        path.append(neighbour)
        current = neighbour
    return path


def _count_fittings(
    endpoints: set[tuple],
    seg_ids: list[int],
    segments: list[tuple],
    adj: dict,
) -> dict[str, int]:
    """Count HVAC fittings inside a connected component.

    elbow_45 / elbow_90: degree-2 vertex where adjoining segments bend.
    tee: degree-3 vertex.
    cross: degree-4+ vertex.
    transition: degree-2 vertex where neighboring layer-encoded sizes differ.
    """
    seg_set = set(seg_ids)
    counts = {"elbow_45": 0, "elbow_90": 0, "tee": 0, "cross": 0, "transition": 0}

    for endpoint in endpoints:
        # Restrict adjacency to this component only.
        incident = [
            (neighbour, sid)
            for neighbour, sid in adj.get(endpoint, [])
            if sid in seg_set
        ]
        # Deduplicate: a segment whose both endpoints snap to the same vertex
        # would otherwise show up twice — that's a degenerate loop, ignore.
        unique_incident: dict[int, tuple] = {}
        for neighbour, sid in incident:
            unique_incident.setdefault(sid, (neighbour, sid))
        incident = list(unique_incident.values())
        degree = len(incident)

        if degree <= 1:
            continue
        if degree == 2:
            (n1, sid_a), (n2, sid_b) = incident
            angle = _bend_angle_deg(endpoint, n1, n2)
            if angle >= ELBOW_MIN_ANGLE_DEG:
                if angle >= ELBOW_45_THRESHOLD_DEG:
                    counts["elbow_90"] += 1
                else:
                    counts["elbow_45"] += 1
            # Transitions: same straight run but the size-encoding layer differs.
            size_a = _size_token(segments[sid_a][3])
            size_b = _size_token(segments[sid_b][3])
            if size_a and size_b and size_a != size_b:
                counts["transition"] += 1
        elif degree == 3:
            counts["tee"] += 1
        elif degree >= 4:
            counts["cross"] += 1

    return counts


def _bend_angle_deg(vertex: tuple, n1: tuple, n2: tuple) -> float:
    """Angle in degrees between (vertex→n1) and (vertex→n2). 0° means
    perfectly continuous; 180° means reversed onto itself."""
    v1x, v1y = n1[0] - vertex[0], n1[1] - vertex[1]
    v2x, v2y = n2[0] - vertex[0], n2[1] - vertex[1]
    n1_len = math.hypot(v1x, v1y)
    n2_len = math.hypot(v2x, v2y)
    if n1_len == 0 or n2_len == 0:
        return 0.0
    cos_theta = (v1x * v2x + v1y * v2y) / (n1_len * n2_len)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    interior = math.degrees(math.acos(cos_theta))
    # interior is the angle BETWEEN the two outgoing vectors. Straight-through
    # gives 180°; 90° elbow gives 90°. We report the deflection from straight.
    return abs(180.0 - interior)


def _size_token(layer_name: str | None) -> str | None:
    """Pull a size encoding out of a layer name for transition detection."""
    if not layer_name:
        return None
    import re
    upper = layer_name.upper()
    if (m := re.search(r"(\d+)X(\d+)", upper)):
        return f"{m.group(1)}x{m.group(2)}"
    if (m := re.search(r"(\d+(?:\.\d+)?)[\s-]?(?:RD|IN|INCH|\")", upper)):
        return f"{m.group(1)}\""
    return None


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
    if duct_match and "duct" in mat_type:
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
