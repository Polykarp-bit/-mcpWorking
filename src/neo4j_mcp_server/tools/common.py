from __future__ import annotations

from ..core import _MAX_INPUT_LEN


def validate_required(value: str, field_name: str) -> str:
    """Prüft, ob ein erforderliches Textfeld nicht leer ist."""
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v

