"""
Specification document parser using pdfplumber for text extraction
and Claude API for structured data extraction.
"""
import json
import logging
import re
from dataclasses import dataclass, field

import pdfplumber
import anthropic

from core.config import settings

log = logging.getLogger(__name__)

# CSI MasterFormat Division patterns
SECTION_PATTERN = re.compile(r"SECTION\s+(\d{2}\s+\d{2}\s+\d{2})\s*[-–]\s*(.+?)(?:\n|$)", re.IGNORECASE)
PART_PATTERN = re.compile(r"^PART\s+(\d+)\s*[-–]\s*(.+?)$", re.MULTILINE | re.IGNORECASE)


@dataclass
class SpecSectionData:
    section_number: str
    section_title: str
    raw_text: str
    structured_data: dict = field(default_factory=dict)
    page_start: int = 0
    page_end: int = 0


def extract_spec_sections(file_bytes: bytes) -> list[SpecSectionData]:
    """Extract and chunk a spec PDF into CSI sections."""
    sections = []

    with pdfplumber.open(file_bytes) as pdf:
        full_text_pages = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text_pages.append(text)

        full_text = "\n".join(full_text_pages)

        # Find section boundaries
        matches = list(SECTION_PATTERN.finditer(full_text))

        for i, match in enumerate(matches):
            section_num = match.group(1).replace(" ", " ")  # normalize spaces
            section_title = match.group(2).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            section_text = full_text[start_pos:end_pos]

            # Estimate page numbers
            chars_per_page = len(full_text) / max(len(full_text_pages), 1)
            page_start = max(1, int(start_pos / chars_per_page) + 1)
            page_end = max(page_start, int(end_pos / chars_per_page) + 1)

            sections.append(SpecSectionData(
                section_number=section_num,
                section_title=section_title,
                raw_text=section_text[:8000],  # truncate for storage
                page_start=page_start,
                page_end=page_end,
            ))

    # Fallback: if no CSI sections found, treat whole doc as one section
    if not sections:
        full_text = "\n".join(full_text_pages)
        sections.append(SpecSectionData(
            section_number="",
            section_title="General",
            raw_text=full_text[:8000],
        ))

    return sections


async def analyze_section_with_claude(section: SpecSectionData) -> dict:
    """
    Use Claude to extract structured data from a spec section.
    Returns: materials, products, standards, requirements, submittal_items
    """
    if not settings.anthropic_api_key:
        return {}

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Analyze this construction specification section and extract structured data.
Return ONLY valid JSON with these fields:

{{
  "materials": [
    {{"name": "...", "size": "...", "standard": "...", "notes": "..."}}
  ],
  "products": [
    {{"category": "...", "description": "...", "manufacturer_options": ["..."], "model_series": "..."}}
  ],
  "standards": ["UL 508A", "ASHRAE 90.1", ...],
  "installation_requirements": ["..."],
  "submittal_requirements": ["..."],
  "testing_requirements": ["..."],
  "warranty_requirements": {{"duration": "...", "type": "..."}}
}}

SPEC SECTION {section.section_number} — {section.section_title}:
{section.raw_text[:4000]}
"""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        log.warning(f"Claude spec analysis failed for section {section.section_number}: {e}")

    return {}


async def generate_embeddings(text: str) -> list[float]:
    """Generate sentence-transformer embeddings for spec section text."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.embedding_model)
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        log.warning(f"Embedding generation failed: {e}")
        return []


async def classify_spec_division(filename: str, first_page_text: str) -> str | None:
    """Guess the MasterFormat division from filename and content."""
    text_upper = (filename + " " + first_page_text).upper()
    division_hints = {
        "23": ["HVAC", "MECHANICAL", "HEATING", "COOLING", "VENTILATION", "AIR CONDITIONING", "DUCTWORK"],
        "22": ["PLUMBING", "DOMESTIC WATER", "SANITARY", "DRAINAGE"],
        "26": ["ELECTRICAL", "POWER", "LIGHTING", "CONDUIT", "WIRING"],
        "21": ["FIRE SUPPRESSION", "SPRINKLER"],
        "28": ["FIRE ALARM", "DETECTION"],
    }
    for division, keywords in division_hints.items():
        if any(kw in text_upper for kw in keywords):
            return division
    return None
