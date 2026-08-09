"""Stable JSON error contract for the local review server."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSpec:
    status: int


# This is the complete vocabulary reserved by the #49 server protocol. Some
# entries are raised only by later children, but defining them here keeps every
# endpoint on one contract from the start.
ERROR_REGISTRY = {
    "bad_request": ErrorSpec(400),
    "invalid_host": ErrorSpec(400),
    "authentication_required": ErrorSpec(401),
    "invalid_bootstrap": ErrorSpec(401),
    "expired_bootstrap": ErrorSpec(401),
    "invalid_origin": ErrorSpec(403),
    "not_found": ErrorSpec(404),
    "illegal_state": ErrorSpec(409),
    "stale_report": ErrorSpec(409),
    "stale_verdicts": ErrorSpec(409),
    "overrides_changed": ErrorSpec(409),
    "length_required": ErrorSpec(411),
    "payload_too_large": ErrorSpec(413),
    "unsupported_media_type": ErrorSpec(415),
    "invalid_export": ErrorSpec(422),
    "internal_error": ErrorSpec(500),
    "report_failed": ErrorSpec(500),
}


class ApiError(Exception):
    """A registered API failure with a safe human-readable message."""

    def __init__(self, code: str, status: int, message: str) -> None:
        spec = ERROR_REGISTRY.get(code)
        if spec is None:
            raise ValueError(f"unregistered API error code {code!r}")
        if spec.status != status:
            raise ValueError(
                f"API error {code!r} is registered as {spec.status}, not {status}"
            )
        if not isinstance(message, str) or not message:
            raise ValueError("API error message must be a non-empty string")
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


def error_payload(code: str, message: str) -> dict[str, dict[str, str]]:
    """Build the one permitted server error shape."""
    if code not in ERROR_REGISTRY:
        raise ValueError(f"unregistered API error code {code!r}")
    return {"error": {"code": code, "message": message}}
