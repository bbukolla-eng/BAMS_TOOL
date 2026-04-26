"""
Generate proposal Scope of Work, Inclusions, and Exclusions text using
Claude, grounded in the project's takeoff items and matched spec sections.

The static template that the existing PDF generator emits is fine for a
draft, but it leaves the most important sections empty. With the takeoff
already aggregated and (optionally) spec-linked, Claude can produce shop-
specific scope language for a Division 23 bid in seconds.

Public surface:
    propose_scope(project_id, db) -> dict
        Returns {scope_of_work, inclusions, exclusions, clarifications}.
        Falls back to a deterministic stub when no API key is set.
    write_proposal_text_into(proposal, db) -> dict
        Generates and persists the four fields onto a Proposal row when
        any of them are blank. Manual edits are never overwritten.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ai.json_repair import parse_json_payload

log = logging.getLogger(__name__)

DEFAULT_MAX_TAKEOFF_LINES = 60
DEFAULT_MAX_SPEC_SECTIONS = 25


async def propose_scope(project_id: int, db) -> dict[str, str]:
    """Build the scope dict from takeoff + spec context. Calls Claude when
    a key is configured; otherwise returns a deterministic skeleton so the
    proposal still has usable text downstream."""
    context = await _gather_project_context(project_id, db)
    from core.config import settings  # heavy import (pydantic-settings); load lazily
    if not settings.anthropic_api_key:
        return _deterministic_fallback(context)

    prompt = _build_prompt(context)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        parsed = parse_json_payload(text)
        if parsed:
            return _coerce_scope_dict(parsed, context)
    except Exception as exc:
        log.warning("Claude proposal scope generation failed: %s", exc)
    return _deterministic_fallback(context)


async def write_proposal_text_into(proposal, db) -> dict[str, str]:
    """Fill in any blank scope fields on the proposal. Returns the dict that
    was applied so callers can echo it to the API response."""
    scope = await propose_scope(proposal.project_id, db)
    applied: dict[str, str] = {}
    for field in ("scope_of_work", "inclusions", "exclusions", "clarifications"):
        if not getattr(proposal, field, None) and scope.get(field):
            setattr(proposal, field, scope[field])
            applied[field] = scope[field]
    return applied


async def _gather_project_context(project_id: int, db) -> dict[str, Any]:
    from sqlalchemy import select

    from models.project import Project
    from models.specification import Specification, SpecSection
    from models.takeoff import TakeoffItem

    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()

    takeoff_q = (
        select(TakeoffItem)
        .where(TakeoffItem.project_id == project_id)
        .order_by(
            TakeoffItem.category,
            TakeoffItem.csi_code,
            TakeoffItem.description,
        )
    )
    takeoff = (await db.execute(takeoff_q)).scalars().all()
    takeoff_lines = _summarize_takeoff(takeoff)

    spec_q = (
        select(SpecSection)
        .join(Specification, SpecSection.specification_id == Specification.id)
        .where(Specification.project_id == project_id)
        .order_by(SpecSection.section_number)
    )
    sections = (await db.execute(spec_q)).scalars().all()
    spec_lines = _summarize_specs(sections)

    return {
        "project_name": getattr(project, "name", None) or f"Project {project_id}",
        "project_address": getattr(project, "address", None),
        "takeoff_lines": takeoff_lines,
        "spec_lines": spec_lines,
        "takeoff_categories": _category_summary(takeoff),
        "has_division_23_specs": any(
            s.section_number and s.section_number.startswith("23 ")
            for s in sections
        ),
    }


def _summarize_takeoff(items: list, limit: int = DEFAULT_MAX_TAKEOFF_LINES) -> list[str]:
    out: list[str] = []
    for item in items[:limit]:
        qty = getattr(item, "adjusted_quantity", None) or item.quantity or 0
        unit = item.unit or ""
        desc = item.description or item.csi_code or item.category or "Item"
        out.append(f"- {qty:.1f} {unit} — {desc}")
    if len(items) > limit:
        out.append(f"… plus {len(items) - limit} additional line items")
    return out


def _summarize_specs(sections: list, limit: int = DEFAULT_MAX_SPEC_SECTIONS) -> list[str]:
    out = []
    for s in sections[:limit]:
        title = s.section_title or "Untitled"
        if s.section_number:
            out.append(f"- {s.section_number} — {title}")
        else:
            out.append(f"- {title}")
    if len(sections) > limit:
        out.append(f"… plus {len(sections) - limit} additional sections")
    return out


def _category_summary(items: list) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[item.category or "uncategorized"] += 1
    return dict(counts)


def _build_prompt(context: dict[str, Any]) -> str:
    takeoff_block = "\n".join(context["takeoff_lines"]) or "(no takeoff items)"
    spec_block = "\n".join(context["spec_lines"]) or "(no spec sections)"
    div23 = "Yes" if context["has_division_23_specs"] else "No"
    address = context.get("project_address") or "n/a"
    return f"""You are drafting a Division 23 (Mechanical / HVAC) bid proposal.
Generate plain-prose construction-shop language for the four fields below,
returning ONLY valid JSON in this exact shape:

{{
  "scope_of_work": "...",
  "inclusions": "...",
  "exclusions": "...",
  "clarifications": "..."
}}

Rules:
- Write in plain English, like a senior estimator. No marketing language.
- Each field is one paragraph or a bullet list (use "- " on each line).
- Be specific about systems based on the takeoff: name ductwork, piping
  services (CHW/HW/CW/etc.), equipment types, and counts where useful.
- Inclusions: what we ARE doing.
- Exclusions: what we are NOT (controls programming by Owner's BAS vendor,
  power wiring by EC, structural support, painting, etc.) — pick the
  realistic exclusions for an HVAC sub.
- Clarifications: assumptions about scope ambiguity, ceiling access,
  hours of work, escalation. Limit to 3-5 lines.
- Do not invent equipment that isn't in the takeoff.

Project: {context['project_name']}
Address: {address}
Division 23 specs available: {div23}

TAKEOFF SUMMARY (most prominent line items):
{takeoff_block}

SPEC SECTIONS:
{spec_block}
"""


def _coerce_scope_dict(parsed: dict, context: dict[str, Any]) -> dict[str, str]:
    out = _deterministic_fallback(context)
    for k in ("scope_of_work", "inclusions", "exclusions", "clarifications"):
        v = parsed.get(k)
        if isinstance(v, list):
            out[k] = "\n".join(f"- {line}" for line in v if line)
        elif isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out


def _deterministic_fallback(context: dict[str, Any]) -> dict[str, str]:
    """Stable text used when Claude is unavailable. Built from takeoff
    categories so it still beats the empty-section default."""
    cats = context.get("takeoff_categories") or {}
    has_duct = any("duct" in k for k in cats)
    has_pipe = any("pipe" in k for k in cats)
    has_equipment = any(k in cats for k in ("ahu", "rtu", "fcu", "boiler", "chiller"))

    scope_lines = ["Furnish and install Division 23 mechanical scope per drawings and specifications, including:"]
    if has_duct:
        scope_lines.append("- Ductwork (supply, return, exhaust, outside air) including hangers, supports, and sealing")
    if has_pipe:
        scope_lines.append("- Hydronic and refrigerant piping with insulation, supports, and pressure-testing")
    if has_equipment:
        scope_lines.append("- Equipment receipt, set-in-place, hookup, and start-up")
    if not (has_duct or has_pipe or has_equipment):
        scope_lines.append("- See attached takeoff for line items")

    inclusions = (
        "- Materials and labor for items shown on the takeoff\n"
        "- Submittals, shop drawings, and as-builts\n"
        "- Test, adjust, and balance per Spec Section 23 05 93\n"
        "- Manufacturer-supplied start-up reports and warranties"
    )
    exclusions = (
        "- Power wiring to mechanical equipment (by Electrical Contractor)\n"
        "- Controls programming and BAS head-end (by Owner's controls vendor)\n"
        "- Painting and architectural finishes\n"
        "- Structural steel for equipment dunnage\n"
        "- Roofing patch / flashing\n"
        "- Permits and impact fees beyond mechanical permit"
    )
    clarifications = (
        "- Pricing assumes normal-hours work; premium time is excluded.\n"
        "- Ceiling access provided open by GC.\n"
        "- Equipment lead time per current manufacturer schedules; escalation reserved beyond 60 days."
    )
    return {
        "scope_of_work": "\n".join(scope_lines),
        "inclusions": inclusions,
        "exclusions": exclusions,
        "clarifications": clarifications,
    }
