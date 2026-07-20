"""HAR searching, tokenizing, and matching execution engine."""

import base64
import hashlib
import re
import shlex
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Sequence

from core.models import FIELD_MAP, ParsedEntry

# Checkbox label -> function turning raw bytes into the encoded/hashed string.
ENCODERS: dict[str, Callable[[bytes], str]] = {
    # --- Standard Encodings ---
    "Base64": lambda data: base64.b64encode(data).decode("ascii"),
    "Base32": lambda data: base64.b32encode(data).decode("ascii"),
    "Hex (Lower)": lambda data: data.hex(),
    "Hex (Upper)": lambda data: data.hex().upper(),
    # --- URL Encodings (Multi-Pass) ---
    "URL Encode": urllib.parse.quote_from_bytes,
    "Double URL Encode": lambda data: urllib.parse.quote(urllib.parse.quote_from_bytes(data)),
    "Triple URL Encode": lambda data: urllib.parse.quote(
        urllib.parse.quote(urllib.parse.quote_from_bytes(data))
    ),
    # --- Standard Hashes (Hex Digests) ---
    "MD5": lambda data: hashlib.md5(data).hexdigest(),
    "SHA1": lambda data: hashlib.sha1(data).hexdigest(),
    "SHA256": lambda data: hashlib.sha256(data).hexdigest(),
    "SHA512": lambda data: hashlib.sha512(data).hexdigest(),
    # --- Hash then Encode (Raw Digest -> Base64) ---
    # Extremely common in API headers, tokens, and basic/custom auth signatures (e.g., Content-MD5)
    "MD5 -> Base64": lambda data: base64.b64encode(hashlib.md5(data).digest()).decode("ascii"),
    "SHA256 -> Base64": lambda data: base64.b64encode(hashlib.sha256(data).digest()).decode(
        "ascii"
    ),
    # --- Encode then Hash (Encoded String -> Hash Digest) ---
    # Captures instances where applications hash an already-obfuscated or serialized string
    "URL Encode -> MD5": lambda data: hashlib.md5(
        urllib.parse.quote_from_bytes(data).encode("utf-8")
    ).hexdigest(),
    "URL Encode -> SHA256": lambda data: hashlib.sha256(
        urllib.parse.quote_from_bytes(data).encode("utf-8")
    ).hexdigest(),
    "Base64 -> MD5": lambda data: hashlib.md5(base64.b64encode(data)).hexdigest(),
    "Base64 -> SHA256": lambda data: hashlib.sha256(base64.b64encode(data)).hexdigest(),
}

# Stable, ordered list for populating UI checkboxes/multiselects.
ENCODING_OPTIONS: list[str] = list(ENCODERS.keys())


@dataclass(frozen=True)
class MatchReason:
    """Explains a single match: which term hit which field, plain or encoded."""

    term: str
    attr: str
    encoding: str | None  # None means a plain-text match


@dataclass
class MatchResult:
    """Outcome of matching an entry against a query."""

    matched: bool
    reasons: list[MatchReason] = field(default_factory=list[MatchReason])


def encode_variants(value: str, encodings: set[str]) -> dict[str, str]:
    """Return {encoding_name: transformed_value} for each selected encoding/hash."""
    if not value or not encodings:
        return {}
    raw = value.encode("utf-8", errors="ignore")
    variants: dict[str, str] = {}
    for name in encodings:
        encoder = ENCODERS.get(name)
        if encoder is None:
            continue
        try:
            variants[name] = encoder(raw)
        except ValueError:
            continue
    return variants


def _collect_reasons(
    entry: ParsedEntry,
    attrs: Sequence[str],
    term: str,
    variants: dict[str, str],
) -> list[MatchReason]:
    """Check `term` (plain, case-insensitive) and each encoded variant (case-sensitive)
    against every attribute in `attrs`, recording where each hit came from."""
    reasons: list[MatchReason] = []
    for attr in attrs:
        text = str(getattr(entry, attr))
        if term.lower() in text.lower():
            reasons.append(MatchReason(term=term, attr=attr, encoding=None))
        for name, variant in variants.items():
            if variant in text:
                reasons.append(MatchReason(term=term, attr=attr, encoding=name))
    return reasons


def match_term(
    entry: ParsedEntry,
    term: str,
    default_field: str,
    encodings: set[str],
) -> tuple[bool, list[MatchReason]]:
    """Match against a term in an entry"""
    is_negated = False
    # Identify and isolate negated query markers (e.g., -status:200)
    if term.startswith("-") and len(term) > 1:
        is_negated = True
        term = term[1:]

    term = term.strip("'\"")
    reasons: list[MatchReason] = []

    # Route field-specific searches (e.g., url:google, cookies:sid)
    # Exclude normal http(s) protocols so direct URL searches don't break
    if ":" in term and not term.startswith(("http:", "https:")):
        field_name, value = term.split(":", 1)
        field_name = field_name.lower()
        if field_name in FIELD_MAP:
            if field_name == "status" and re.fullmatch(r"[1-5]xx", value.lower()):
                if entry.status.startswith(value[0]):
                    reasons.append(MatchReason(term=value, attr="status", encoding=None))
            else:
                variants = encode_variants(value, encodings)
                reasons = _collect_reasons(entry, FIELD_MAP[field_name], value, variants)
        else:
            attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
            variants = encode_variants(term, encodings)
            reasons = _collect_reasons(entry, attrs, term, variants)
    else:
        # Default fallback standard search
        attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
        variants = encode_variants(term, encodings)
        reasons = _collect_reasons(entry, attrs, term, variants)

    matched = bool(reasons)
    if is_negated:
        # A negated term explains an *absence*, not a positive match - no reasons to show.
        return (not matched, [])
    return (matched, reasons)


def entry_matches(
    entry: ParsedEntry,
    query: str,
    default_field: str,
    methods: set[str],
    encodings: set[str] | None = None,
) -> MatchResult:
    """Evaluate whether an entry satisfies selected methods and tokenized search terms,
    returning both the verdict and which fields/encodings caused it."""
    if methods and entry.method not in methods:
        return MatchResult(matched=False)
    if not query:
        return MatchResult(matched=True)

    try:
        terms = shlex.split(query)
    except ValueError:
        # Prevent app-crashes on incomplete/unclosed quote structures
        terms = query.split()

    active_encodings = encodings or set()
    all_reasons: list[MatchReason] = []
    for term in terms:
        matched, reasons = match_term(entry, term, default_field, active_encodings)
        if not matched:
            return MatchResult(matched=False)
        all_reasons.extend(reasons)
    return MatchResult(matched=True, reasons=all_reasons)
