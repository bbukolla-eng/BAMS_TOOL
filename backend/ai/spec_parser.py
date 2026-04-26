"""
Specification document parser using pdfplumber for text extraction
and Claude API for structured data extraction.
"""
import io
import json
import logging
import re
from dataclasses import dataclass, field

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
    import pdfplumber  # heavy dep; load lazily so unit tests of pure helpers don't pull it
    sections = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
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

    import anthropic  # heavy dep; only loaded when we have a key
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
        parsed = parse_json_payload(text)
        if parsed is not None:
            return parsed
        log.warning(
            "Spec section %s: Claude returned no parseable JSON",
            section.section_number,
        )
    except Exception as e:
        log.warning(f"Claude spec analysis failed for section {section.section_number}: {e}")

    return {}


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json_payload(text: str) -> dict | None:
    """Robustly pull a JSON object out of an LLM response.

    Handles three common shapes Claude (and other LLMs) emit:
      1. raw JSON, possibly with leading/trailing prose
      2. JSON inside ```json ... ``` fences
      3. JSON that's been truncated mid-way (closes brackets we still need)

    Returns the parsed dict, or None if nothing recoverable was found.
    """
    if not text:
        return None
    candidates: list[str] = []

    # Fenced code blocks first — that's the LLM's most explicit signal.
    candidates.extend(m.strip() for m in _FENCE_RE.findall(text))

    # Then any balanced top-level JSON object the model emitted directly.
    if not candidates:
        candidates.append(text.strip())

    for raw in candidates:
        if not raw:
            continue
        balanced = _largest_balanced_object(raw)
        if not balanced:
            continue
        try:
            return json.loads(balanced)
        except json.JSONDecodeError:
            # Final attempt: close any unfinished brackets.
            repaired = _repair_truncated_json(balanced)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    continue
    return None


def _largest_balanced_object(text: str) -> str | None:
    """Return the longest substring that begins with '{' and ends at its
    matching '}'. Skips braces inside string literals."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _repair_truncated_json(text: str) -> str | None:
    """Best-effort fix when the LLM cuts off mid-output. Strategy:

    1. If we ended inside a string, close it at end of input and balance braces.
    2. Otherwise, try to walk back from the end of input to a point where the
       structure is plausibly complete (after a `}` or after a `"` closing a
       value), and balance from there.
    3. As a last resort, return the raw text with closing brackets — the
       caller still json.loads it inside try/except.

    Returns None if there's no opening `{` at all.
    """
    if "{" not in text:
        return None

    final_state = _scan_state(text)

    # Case 1: cut mid-string — close the quote and balance the rest.
    if final_state["in_string"]:
        candidate = text + '"' \
            + "]" * max(0, final_state["depth_square"]) \
            + "}" * max(0, final_state["depth_curly"])
        return candidate

    # Case 2: not in a string. Walk back to a structurally clean cut point.
    candidate = _close_at_clean_point(text, final_state)
    return candidate


def _scan_state(text: str) -> dict:
    depth_curly = 0
    depth_square = 0
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth_curly += 1
        elif ch == "}":
            depth_curly -= 1
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            depth_square -= 1
    return {
        "depth_curly": depth_curly,
        "depth_square": depth_square,
        "in_string": in_string,
    }


def _close_at_clean_point(text: str, final_state: dict) -> str:
    """Trim trailing content that would leave the JSON in an invalid mid-value
    state (orphan key+colon, half-typed array, etc.) and close all open brackets.
    """
    trimmed = text.rstrip()
    while trimmed and trimmed[-1] in ",:":
        trimmed = trimmed[:-1].rstrip()
        if trimmed.endswith('"'):
            # Drop the trailing quoted key (everything back to the opening quote)
            opening = trimmed.rfind('"', 0, -1)
            if opening >= 0:
                trimmed = trimmed[:opening].rstrip().rstrip(",")
    candidate = trimmed
    candidate += "]" * max(0, final_state["depth_square"])
    candidate += "}" * max(0, final_state["depth_curly"])
    return candidate


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
