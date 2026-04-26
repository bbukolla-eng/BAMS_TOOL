"""
Match spec sections to drawing elements by semantic similarity.

A Division 23 spec section (e.g. "23 31 13 — Metal Ducts") describes
construction requirements; the drawing shows runs and equipment that those
requirements govern. Linking the two lets the bid pipeline:
  - Surface "this AHU on the drawing must comply with Section 23 73 13" warnings
  - Pre-populate submittal logs from drawing detections
  - Drive RFI generation when a spec requirement has no drawing match

Approach: cosine similarity between the spec section's existing embedding
and an on-the-fly embedding of each Symbol/MaterialRun's descriptive text.
Threshold defaults to 0.55, tunable per project.
"""
from __future__ import annotations

import logging
import math

log = logging.getLogger(__name__)

DEFAULT_LINK_THRESHOLD = 0.55
TOP_MATCHES_PER_ITEM = 3


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for two vectors. Returns 0 if either is empty."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / math.sqrt(na * nb)


def describe_symbol(symbol_type: str, properties: dict | None) -> str:
    """Render a symbol into the descriptive text used for embedding."""
    parts = [symbol_type.replace("_", " ")]
    if not properties:
        return parts[0]
    if (size := properties.get("size")):
        parts.append(f"size {size}")
    if (inlet := properties.get("inlet_size")):
        parts.append(f"inlet {inlet}")
    if (cfm := properties.get("cfm")):
        parts.append(f"{cfm:g} CFM")
    if (tons := properties.get("tons")):
        parts.append(f"{tons:g} ton")
    if (mbh := properties.get("mbh")):
        parts.append(f"{mbh:g} MBH")
    if (gpm := properties.get("gpm")):
        parts.append(f"{gpm:g} GPM")
    if (model := properties.get("model")):
        parts.append(f"model {model}")
    if (mfr := properties.get("manufacturer")):
        parts.append(mfr)
    return ", ".join(parts)


def describe_run(material_type: str, size: str | None) -> str:
    text = material_type.replace("_", " ")
    if size:
        text += f", {size}"
    return text


def _section_relevant_to_division(section_number: str | None, division: str = "23") -> bool:
    """Cheap pre-filter: only consider sections in the same division so we
    don't waste similarity calls comparing electrical to mechanical."""
    if not section_number:
        return True
    return section_number.strip().startswith(f"{division} ")


async def link_spec_to_project_drawings(
    project_id: int,
    *,
    threshold: float = DEFAULT_LINK_THRESHOLD,
    division_hint: str | None = "23",
    embed_func=None,
) -> dict[str, int]:
    """Compute and persist SpecDrawingLink rows for every Symbol & MaterialRun
    in the project against every SpecSection of the matching division.

    Idempotent: existing 'auto' links are recreated; 'manual' links are kept.
    Returns counts: {sections, items, links_created, skipped_no_embedding}.
    """
    from sqlalchemy import delete, select

    from core.database import AsyncSessionLocal
    from models.drawing import Drawing, DrawingPage, MaterialRun, Symbol
    from models.specification import (
        SpecDrawingLink,
        Specification,
        SpecSection,
    )

    if embed_func is None:
        from ai.spec_parser import generate_embeddings
        embed_func = generate_embeddings

    counts = {
        "sections": 0,
        "items": 0,
        "links_created": 0,
        "skipped_no_embedding": 0,
    }

    async with AsyncSessionLocal() as db:
        spec_q = (
            select(SpecSection)
            .join(Specification, SpecSection.specification_id == Specification.id)
            .where(Specification.project_id == project_id)
        )
        spec_rows = (await db.execute(spec_q)).scalars().all()
        sections: list[tuple[SpecSection, list[float]]] = []
        for section in spec_rows:
            if not _section_relevant_to_division(section.section_number, division_hint or ""):
                continue
            embedding = _coerce_embedding(section.embedding)
            if not embedding:
                counts["skipped_no_embedding"] += 1
                continue
            sections.append((section, embedding))
        counts["sections"] = len(sections)
        if not sections:
            return counts

        section_ids = [section.id for section, _ in sections]
        await db.execute(
            delete(SpecDrawingLink).where(
                SpecDrawingLink.spec_section_id.in_(section_ids),
                SpecDrawingLink.match_type == "auto",
            )
        )

        # Walk drawings → pages → symbols + runs in this project.
        drawings_q = select(Drawing).where(Drawing.project_id == project_id)
        drawings = (await db.execute(drawings_q)).scalars().all()
        for drawing in drawings:
            pages_q = select(DrawingPage).where(DrawingPage.drawing_id == drawing.id)
            pages = (await db.execute(pages_q)).scalars().all()
            for page in pages:
                syms = (await db.execute(
                    select(Symbol).where(Symbol.page_id == page.id)
                )).scalars().all()
                for sym in syms:
                    counts["items"] += 1
                    text = describe_symbol(sym.symbol_type, sym.properties)
                    embedding = await embed_func(text)
                    if not embedding:
                        continue
                    matches = _top_matches(embedding, sections, threshold)
                    for section, score in matches:
                        db.add(SpecDrawingLink(
                            spec_section_id=section.id,
                            symbol_id=sym.id,
                            material_run_id=None,
                            match_score=round(score, 4),
                            match_type="auto",
                        ))
                        counts["links_created"] += 1

                runs = (await db.execute(
                    select(MaterialRun).where(MaterialRun.page_id == page.id)
                )).scalars().all()
                for run in runs:
                    counts["items"] += 1
                    text = describe_run(run.material_type, run.size)
                    embedding = await embed_func(text)
                    if not embedding:
                        continue
                    matches = _top_matches(embedding, sections, threshold)
                    for section, score in matches:
                        db.add(SpecDrawingLink(
                            spec_section_id=section.id,
                            symbol_id=None,
                            material_run_id=run.id,
                            match_score=round(score, 4),
                            match_type="auto",
                        ))
                        counts["links_created"] += 1

        await db.commit()

    log.info("Spec→drawing linking for project %s: %s", project_id, counts)
    return counts


def _coerce_embedding(raw) -> list[float] | None:
    """SpecSection.embedding can be a Postgres pgvector, a SQLite text fallback,
    or None. Normalize to list[float]."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        cleaned = raw.strip().lstrip("[").rstrip("]")
        if not cleaned:
            return None
        try:
            return [float(x) for x in cleaned.split(",") if x.strip()]
        except ValueError:
            return None
    if hasattr(raw, "tolist"):
        try:
            return [float(x) for x in raw.tolist()]
        except Exception:
            return None
    try:
        return [float(x) for x in raw]
    except Exception:
        return None


def _top_matches(
    item_embedding: list[float],
    section_embeddings: list[tuple],
    threshold: float,
) -> list[tuple]:
    """Return the top-N (section, score) pairs above threshold."""
    scored = []
    for section, section_emb in section_embeddings:
        score = cosine_similarity(item_embedding, section_emb)
        if score >= threshold:
            scored.append((section, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:TOP_MATCHES_PER_ITEM]
