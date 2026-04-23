"""Spec-to-drawing matching service.

Two-stage approach:
1. Vector search — use cosine similarity on stored spec section embeddings
   against a query vector derived from each symbol/run type description.
   Only available on PostgreSQL (pgvector). Gracefully skipped for SQLite.
2. Keyword / CSI-code matching — always runs as a fallback and supplement.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.drawing import MaterialRun, Symbol
from models.specification import SpecSection

log = logging.getLogger(__name__)

# CSI division-to-HVAC symbol/material type mapping
_DIV_SYMBOL_KEYWORDS: dict[str, list[str]] = {
    "23": ["vav", "ahu", "fcu", "rtu", "diffuser", "grille", "damper", "fan", "coil", "pump", "boiler", "chiller"],
    "22": ["pipe", "valve", "fitting", "pump"],
    "26": ["panel", "transformer", "breaker", "switchboard"],
    "21": ["sprinkler", "riser", "standpipe"],
    "28": ["detector", "horn", "strobe"],
}

_DIV_MATERIAL_KEYWORDS: dict[str, list[str]] = {
    "23": ["duct", "pipe_chw", "pipe_hw", "pipe_cw", "pipe_steam", "pipe_condensate", "insulation"],
    "22": ["pipe_domestic", "pipe_sanitary", "pipe_storm"],
    "26": ["conduit", "cable_tray", "wire"],
    "21": ["pipe_fire"],
}

# Human-readable descriptions for each symbol/material type used to build
# query embeddings for vector similarity search.
_TYPE_DESCRIPTIONS: dict[str, str] = {
    # symbols
    "vav": "variable air volume box VAV terminal unit",
    "ahu": "air handling unit AHU rooftop unit air handler",
    "fcu": "fan coil unit FCU terminal unit",
    "rtu": "rooftop unit RTU packaged unit",
    "diffuser": "supply air diffuser grille register ceiling diffuser",
    "grille": "return air grille exhaust grille",
    "damper": "fire damper smoke damper volume damper balancing damper",
    "fan": "exhaust fan supply fan inline fan",
    "coil": "heating coil cooling coil heat exchanger",
    "pump": "circulating pump chilled water pump hot water pump",
    "boiler": "boiler hot water boiler steam boiler",
    "chiller": "chiller water cooled chiller air cooled chiller refrigeration",
    "sprinkler": "sprinkler head fire suppression",
    "panel": "electrical panel distribution board",
    "transformer": "electrical transformer voltage step down",
    # material runs
    "duct_supply": "supply air ductwork rectangular duct spiral duct",
    "duct_return": "return air duct return ductwork",
    "duct_exhaust": "exhaust duct exhaust air ductwork",
    "pipe_chw": "chilled water pipe CHW supply return",
    "pipe_hw": "hot water pipe HW heating water",
    "pipe_cw": "condenser water pipe cooling tower",
    "pipe_steam": "steam pipe high pressure steam",
    "pipe_condensate": "condensate pipe steam condensate return",
    "pipe_domestic": "domestic water pipe cold water hot water plumbing",
    "pipe_sanitary": "sanitary drain waste vent DWV",
    "pipe_storm": "storm drain roof drain stormwater",
    "pipe_fire": "fire sprinkler pipe standpipe fire suppression",
    "conduit": "electrical conduit EMT rigid conduit wire way",
    "cable_tray": "cable tray wire management",
    "insulation": "pipe insulation duct insulation thermal insulation",
}


async def find_spec_drawing_matches(spec_id: int, section_id: int, db: AsyncSession) -> list[dict]:
    section_result = await db.execute(select(SpecSection).where(SpecSection.id == section_id))
    section = section_result.scalar_one_or_none()
    if not section:
        return []

    # Determine CSI division from section_number (e.g. "23 31 13" → "23")
    division = None
    if section.section_number:
        parts = section.section_number.strip().split()
        if parts:
            division = parts[0][:2]

    # Find the project's drawing pages to scope the search
    spec_result = await db.execute(
        text(
            "SELECT DISTINCT dp.id FROM drawing_pages dp "
            "JOIN drawings d ON d.id = dp.drawing_id "
            "JOIN specifications s ON s.project_id = d.project_id "
            "WHERE s.id = :spec_id"
        ),
        {"spec_id": spec_id},
    )
    page_ids = [row[0] for row in spec_result.fetchall()]
    if not page_ids:
        return []

    matches: list[dict] = []

    # ── Stage 1: Vector similarity search ───────────────────────────────────
    # Only available on PostgreSQL when the section has a stored embedding.
    if section.embedding is not None:
        try:
            vec_matches = await _vector_search(section, page_ids, db)
            matches.extend(vec_matches)
        except Exception as exc:
            log.debug("Vector search skipped: %s", exc)

    # ── Stage 2: Keyword / CSI-code matching ────────────────────────────────
    keyword_matches = await _keyword_search(section, page_ids, division, db)

    # Merge: if a symbol/run already has a vector match, boost its score
    seen_symbols: dict[int, dict] = {m["symbol_id"]: m for m in matches if m.get("type") == "symbol"}
    seen_runs: dict[int, dict] = {m["material_run_id"]: m for m in matches if m.get("type") == "material_run"}

    for km in keyword_matches:
        if km["type"] == "symbol":
            sid = km["symbol_id"]
            if sid in seen_symbols:
                seen_symbols[sid]["score"] = min(1.0, seen_symbols[sid]["score"] + km["score"] * 0.3)
            else:
                matches.append(km)
                seen_symbols[sid] = km
        else:
            rid = km["material_run_id"]
            if rid in seen_runs:
                seen_runs[rid]["score"] = min(1.0, seen_runs[rid]["score"] + km["score"] * 0.3)
            else:
                matches.append(km)
                seen_runs[rid] = km

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:30]


async def _vector_search(section: SpecSection, page_ids: list[int], db: AsyncSession) -> list[dict]:
    """Return symbol/run matches ranked by cosine similarity to the section embedding.

    Uses raw SQL so we don't need to import pgvector in the service layer.
    Raises an exception (silently swallowed by caller) when pgvector isn't
    available (SQLite desktop mode or missing extension).
    """
    # Deserialise the stored embedding.  In PostgreSQL mode it may come back
    # as a list of floats; in Text/SQLite mode it comes back as a JSON string.
    embedding = section.embedding
    if isinstance(embedding, str):
        try:
            embedding = json.loads(embedding)
        except (ValueError, TypeError):
            return []
    if not embedding or not isinstance(embedding, (list, tuple)):
        return []

    results: list[dict] = []

    # ── Find matching spec sections in *other* specs for the same project ──
    # (The section's own embedding describes WHAT the spec calls for.
    #  We search across symbols by building a per-type embedding on the fly.)

    # Build query embeddings for every known type description
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    except Exception:
        return []

    # Score each symbol type in this project against the section embedding
    type_scores: dict[str, float] = {}
    for type_key, description in _TYPE_DESCRIPTIONS.items():
        type_vec = _model.encode(description, normalize_embeddings=True).tolist()
        # Cosine similarity = dot product of unit vectors
        import numpy as np
        sec_vec = np.array(embedding, dtype=float)
        t_vec = np.array(type_vec, dtype=float)
        sec_norm = np.linalg.norm(sec_vec)
        t_norm = np.linalg.norm(t_vec)
        if sec_norm > 0 and t_norm > 0:
            sim = float(np.dot(sec_vec / sec_norm, t_vec / t_norm))
        else:
            sim = 0.0
        if sim > 0.3:  # threshold — only meaningful matches
            type_scores[type_key] = round(sim, 4)

    if not type_scores:
        return []

    # Retrieve symbols/runs whose types match any high-similarity type
    matched_types = list(type_scores.keys())

    sym_q = select(Symbol).where(
        Symbol.page_id.in_(page_ids),
        Symbol.symbol_type.in_(matched_types),
    ).limit(15)
    sym_result = await db.execute(sym_q)
    for sym in sym_result.scalars().all():
        score = type_scores.get(sym.symbol_type, 0.3)
        results.append({
            "type": "symbol",
            "symbol_id": sym.id,
            "symbol_type": sym.symbol_type,
            "label": sym.label,
            "score": score,
            "match_method": "vector",
        })

    run_q = select(MaterialRun).where(
        MaterialRun.page_id.in_(page_ids),
        MaterialRun.material_type.in_(matched_types),
    ).limit(15)
    run_result = await db.execute(run_q)
    for run in run_result.scalars().all():
        score = type_scores.get(run.material_type, 0.3)
        results.append({
            "type": "material_run",
            "material_run_id": run.id,
            "material_type": run.material_type,
            "length_ft": run.length_ft,
            "size": run.size,
            "score": score,
            "match_method": "vector",
        })

    return results


async def _keyword_search(
    section: SpecSection, page_ids: list[int], division: str | None, db: AsyncSession
) -> list[dict]:
    """CSI division + keyword matching — always available, no ML dependencies."""
    matches: list[dict] = []

    sym_keywords = _DIV_SYMBOL_KEYWORDS.get(division or "", [])
    sym_q = select(Symbol).where(Symbol.page_id.in_(page_ids))
    if sym_keywords:
        from sqlalchemy import func, or_
        sym_q = sym_q.where(
            or_(*[func.lower(Symbol.symbol_type).contains(kw) for kw in sym_keywords])
        )
    sym_q = sym_q.limit(20)
    sym_result = await db.execute(sym_q)
    for sym in sym_result.scalars().all():
        score = _keyword_score(section, sym.symbol_type, sym.label, division)
        if score > 0:
            matches.append({
                "type": "symbol",
                "symbol_id": sym.id,
                "symbol_type": sym.symbol_type,
                "label": sym.label,
                "score": round(score, 3),
                "match_method": "keyword",
            })

    mat_keywords = _DIV_MATERIAL_KEYWORDS.get(division or "", [])
    run_q = select(MaterialRun).where(MaterialRun.page_id.in_(page_ids))
    if mat_keywords:
        from sqlalchemy import func, or_
        run_q = run_q.where(
            or_(*[func.lower(MaterialRun.material_type).contains(kw) for kw in mat_keywords])
        )
    run_q = run_q.limit(20)
    run_result = await db.execute(run_q)
    for run in run_result.scalars().all():
        score = _keyword_score(section, run.material_type, run.spec_reference, division)
        if score > 0:
            matches.append({
                "type": "material_run",
                "material_run_id": run.id,
                "material_type": run.material_type,
                "length_ft": run.length_ft,
                "size": run.size,
                "score": round(score, 3),
                "match_method": "keyword",
            })

    return matches


def _keyword_score(section: SpecSection, primary_type: str, secondary: str | None, division: str | None) -> float:
    """Heuristic score 0–1 based on CSI division and keyword overlap."""
    score = 0.0

    if division:
        kw_list = _DIV_SYMBOL_KEYWORDS.get(division, []) + _DIV_MATERIAL_KEYWORDS.get(division, [])
        pt_lower = (primary_type or "").lower()
        for kw in kw_list:
            if kw in pt_lower:
                score += 0.5
                break

    title_lower = (section.section_title or "").lower()
    pt_lower = (primary_type or "").lower()
    overlap = sum(1 for word in pt_lower.replace("_", " ").split() if word in title_lower)
    score += overlap * 0.2

    if secondary and section.section_number and secondary in section.section_number:
        score += 0.3

    return min(score, 1.0)
