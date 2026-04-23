"""Shared utility helpers for the BAMS backend."""
from __future__ import annotations

from typing import Any


def _row(obj: Any) -> dict:
    """Convert a SQLAlchemy model instance to a plain JSON-safe dict.

    Strips _sa_instance_state and any non-serializable values (lazy-loaded
    relationships, datetime objects are left as-is — FastAPI's jsonable_encoder
    handles those).  Use this everywhere instead of obj.__dict__.
    """
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return d


def _rows(objs) -> list[dict]:
    """Convenience wrapper for a sequence of model instances."""
    return [_row(o) for o in objs]
