"""Deterministic ordering for opaque DIM instance ids.

DIM ids are strings at every application boundary.  They are normally
decimal uint64 values, but callers must not rely on that being true: review
manifests and fixtures can carry leading-zero, non-digit, or future ids.  The
ordering below compares decimal ids by magnitude while preserving the raw
string as the final tie-break and leaves non-decimal values opaque.
"""

from __future__ import annotations


def instance_id_order(value: object) -> tuple:
    """Return the shared total-order key for one raw instance id.

    No conversion or normalization is performed on the value itself.  The
    returned key is for ordering only; all decisions and projections retain
    the caller's original string.
    """
    raw = str(value)
    if raw.isascii() and raw.isdigit():
        magnitude = raw.lstrip("0") or "0"
        return (0, len(magnitude), magnitude, raw)
    return (1, raw)
