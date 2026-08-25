"""Items 8, 13, 14, 15, 16 — validate input, escape output, restrict uploads."""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# A leading one of these turns a spreadsheet cell into a formula. Google Sheets and
# Excel will happily execute =IMPORTXML(...) against an attacker's server on open.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class InvalidIdentifier(ValueError):
    pass


class UploadRejected(ValueError):
    pass


class StrictModel(BaseModel):
    """Base model for every request body (item 8 — block field tampering).

    ``extra="forbid"`` rejects unknown keys instead of ignoring them, so a client
    cannot smuggle ``{"price": 0}`` or ``{"is_admin": true}`` into a payload and hope
    some later refactor starts reading it. ``str_strip_whitespace`` normalises input so
    length limits cannot be dodged with padding.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        str_max_length=10_000,
        validate_assignment=True,
    )


# Bounded string aliases — always give a user-supplied string an explicit ceiling.
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=120)]
MediumText = Annotated[str, StringConstraints(min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(max_length=2_000)]
Slug = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def safe_identifier(value: str, *, kind: str = "uuid") -> str:
    """Validate an identifier that will be used to build a filesystem or URL path.

    Interpolating a raw path parameter into ``Path(dir) / value`` is a directory
    traversal: ``../../etc/passwd`` and absolute paths both escape the directory. The
    fix is an allowlist on shape, not an attempt to strip bad characters.
    """
    if not isinstance(value, str):
        raise InvalidIdentifier("identifier must be a string")

    pattern = _UUID_RE if kind == "uuid" else _SLUG_RE
    if not pattern.match(value):
        raise InvalidIdentifier(f"invalid {kind}")
    return value


def escape_html(value: object) -> str:
    """Escape user content before it goes into HTML (item 15).

    Covers ``&<>"'`` so the result is safe in both element text and quoted attributes.
    Use this for every value interpolated into an f-string template — including values
    that came back from a third-party API or an LLM, which are not more trustworthy
    than direct user input.
    """
    return html.escape("" if value is None else str(value), quote=True)


def escape_attr(value: object) -> str:
    """Escape a value for an HTML attribute and strip control characters."""
    text = "" if value is None else str(value)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    return html.escape(text, quote=True)


def sanitize_for_spreadsheet(value: object) -> str:
    """Neutralise CSV/spreadsheet formula injection (the item-13 analogue for Sheets).

    Anything appended to a spreadsheet with USER_ENTERED — or exported to CSV — is
    parsed as a formula when it starts with = + - @. Prefixing a single quote makes the
    cell literal text while still displaying the original value.
    """
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def validate_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
    *,
    allowed_extensions: frozenset[str],
    allowed_content_types: frozenset[str],
    max_bytes: int,
) -> str:
    """Validate an upload and return a safe filename (item 16).

    Checks extension, declared content type and size, and returns a filename stripped
    of any path component. Note that ``content_type`` is client-supplied: treat it as a
    cheap first filter, and for anything executed or rendered later also verify the
    file's magic bytes and store it outside the web root.
    """
    if size_bytes > max_bytes:
        raise UploadRejected(f"file too large (max {max_bytes // 1024} KiB)")
    if size_bytes <= 0:
        raise UploadRejected("empty file")

    # Take the basename only: "../../app/main.py" and "C:\\evil.exe" both collapse here.
    base = re.split(r"[\\/]", filename)[-1].strip()
    if not base or base.startswith("."):
        raise UploadRejected("invalid filename")

    if "." not in base:
        raise UploadRejected("missing file extension")
    extension = base.rsplit(".", 1)[1].lower()
    if extension not in allowed_extensions:
        raise UploadRejected(f"extension .{extension} not allowed")

    if content_type.split(";")[0].strip().lower() not in allowed_content_types:
        raise UploadRejected(f"content type {content_type} not allowed")

    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe[:120]
