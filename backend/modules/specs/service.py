from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from models.specification import SpecSection, SpecDrawingLink
from models.drawing import Symbol, MaterialRun, DrawingPage


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

    matches: list[dict] = []

    # ── Vector search (when embedding is available) ─────────────────────────
    if section.embedding is not None:
        try:
            # Find symbols via cosine distance — Symbol doesn't store embeddings yet,
            # so we fall through to keyword matching below
            pass
        except Exception:
            pass

    # ── Keyword / CSI-code matching ──────────────────────────────────────────
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

    # Match symbols
    sym_keywords = _DIV_SYMBOL_KEYWORDS.get(division or "", [])
    sym_q = select(Symbol).where(Symbol.page_id.in_(page_ids))
    if sym_keywords:
        from sqlalchemy import or_, func
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
            })

    # Match material runs
    mat_keywords = _DIV_MATERIAL_KEYWORDS.get(division or "", [])
    run_q = select(MaterialRun).where(MaterialRun.page_id.in_(page_ids))
    if mat_keywords:
        from sqlalchemy import or_, func
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
            })

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:30]


def _keyword_score(section: SpecSection, primary_type: str, secondary: str | None, division: str | None) -> float:
    """Simple heuristic score 0–1 based on CSI division and keyword overlap."""
    score = 0.0

    if division:
        kw_list = _DIV_SYMBOL_KEYWORDS.get(division, []) + _DIV_MATERIAL_KEYWORDS.get(division, [])
        pt_lower = (primary_type or "").lower()
        for kw in kw_list:
            if kw in pt_lower:
                score += 0.5
                break

    # Boost if spec section title contains the type keyword
    title_lower = (section.section_title or "").lower()
    pt_lower = (primary_type or "").lower()
    overlap = sum(1 for word in pt_lower.replace("_", " ").split() if word in title_lower)
    score += overlap * 0.2

    # Boost if spec_reference explicitly set on the run
    if secondary and section.section_number and secondary in section.section_number:
        score += 0.3

    return min(score, 1.0)
