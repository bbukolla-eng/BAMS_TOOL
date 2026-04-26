"""
Robust JSON extraction from LLM output.

Pure stdlib — no FastAPI/SQLAlchemy/Anthropic deps so test environments and
non-API consumers can use these helpers without installing the full backend.
"""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json_payload(text: str | None) -> dict | None:
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
    """Best-effort fix when the LLM cuts off mid-output. See spec_parser tests
    for expected behavior. Returns None if there's no opening `{` at all."""
    if "{" not in text:
        return None

    final_state = _scan_state(text)

    # Case 1: cut mid-string — close the quote and balance the rest.
    if final_state["in_string"]:
        return (
            text + '"'
            + "]" * max(0, final_state["depth_square"])
            + "}" * max(0, final_state["depth_curly"])
        )

    # Case 2: not in a string. Walk back to a structurally clean cut point.
    return _close_at_clean_point(text, final_state)


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
            opening = trimmed.rfind('"', 0, -1)
            if opening >= 0:
                trimmed = trimmed[:opening].rstrip().rstrip(",")
    return (
        trimmed
        + "]" * max(0, final_state["depth_square"])
        + "}" * max(0, final_state["depth_curly"])
    )
