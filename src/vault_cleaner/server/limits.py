"""Named request limits shared by the server children of issue #49."""

MIB = 1024 * 1024

MAX_EXPORT_BYTES = 32 * MIB
MAX_TOTAL_EXPORT_BYTES = 96 * MIB
MAX_JSON_BODY_BYTES = 1 * MIB

# Flask's application-wide guard covers the largest legal individual request.
# The narrower JSON and aggregate-export limits are enforced by the children
# that accept those bodies.
MAX_REQUEST_BODY_BYTES = MAX_EXPORT_BYTES
