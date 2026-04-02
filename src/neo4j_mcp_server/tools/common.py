from __future__ import annotations

from ..core import _MAX_INPUT_LEN


def validate_required(value: str, field_name: str) -> str:
    """Validate that a required string field is not empty."""
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v


def require_confirm(confirm: bool, action: str) -> str | None:
    """Guardrail for destructive operations (human-in-the-loop)."""
    if confirm is True:
        return None
    return (
        "## Confirmation Required\n\n"
        f"Diese Aktion ist destruktiv (**{action}**). "
        "Setze `confirm=true`, um fortzufahren.\n"
    )

