"""HAR searching, tokenizing, and matching execution engine."""

import base64
import hashlib
import re
import shlex
import urllib.parse
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Literal, Mapping, Sequence

from app.core.models import FIELD_MAP, ParsedEntry

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

# URL encoding is a chain (plain -> single -> double -> triple): if a lower
# link in the chain already matched, a higher one matching too just means the
# value has no URL-unsafe characters to encode - it's a no-op, not a distinct
# finding. Other encodings (hashes, Base64, Hex...) aren't chained
_URL_ENCODE_CHAIN: list[str] = ["plain", "URL Encode", "Double URL Encode", "Triple URL Encode"]

# Which side of the exchange a cookie hit came from. Display only: matching
# still runs against the single `cookies_text` attribute, so FIELD_MAP and the
# overlap rules are untouched.
CookieScope = Literal["sent", "received"]

# The one place cookie direction is named. Used verbatim as the Scope column
# in the Cookies tab, the Origin column in Dissemination, and the Field label
# for a cookie hit in match summaries - change it here, it changes everywhere.
COOKIE_LABELS: dict[CookieScope, str] = {
    "sent": "Request Cookie",  # Cookie header on the request
    "received": "Response Cookie",  # Set-Cookie header on the response
}

# The attribute whose hits can be attributed to a side.
_COOKIE_ATTR = "cookies_text"

# Human-readable name for each ParsedEntry attribute a match can hit. Keys
# must match FIELD_MAP's attribute names exactly (e.g. "req_headers_text",
# not "req_headers") - the single place this mapping lives, so the Network
# Log and Dissemination endpoints can't drift apart on it again.
ATTR_LABELS: dict[str, str] = {
    "url": "URL",
    "domain": "Domain",
    "method": "Method",
    "status": "Status",
    "mime": "MIME Type",
    "req_headers_text": "Request Headers",
    "res_headers_text": "Response Headers",
    "req_body": "POST Data",
    "res_body": "Response Body",
    "cookies_text": "Cookies",
    "query_params_text": "Query Params",
}


def attr_label(attr: str) -> str:
    """Human-readable name for a ParsedEntry attribute."""
    return ATTR_LABELS.get(attr, attr.replace("_", " ").title())


def dedupe_redundant_encodings(forms: list[str]) -> list[str]:
    """Collapse a set of matched forms down to the least-encoded link of the
    URL-encoding chain, keeping every non-chain form (hashes, Base64, ...) as-is."""
    chain_hits = [f for f in forms if f in _URL_ENCODE_CHAIN]
    other_hits = [f for f in forms if f not in _URL_ENCODE_CHAIN]

    if not chain_hits:
        return other_hits

    earliest = min(chain_hits, key=_URL_ENCODE_CHAIN.index)
    return [earliest, *other_hits]


@dataclass(frozen=True)
class MatchReason:
    """Explains a single match: which term hit which field, plain or encoded."""

    term: str
    attr: str
    encoding: str | None  # None means a plain-text match
    # Only set for `cookies_text` hits, and only to label them in the UI.
    # None means "not a cookie hit, or the side couldn't be determined".
    scope: CookieScope | None = None


def reason_label(reason: MatchReason) -> str:
    """Field name for display; a cookie hit names its side instead of "Cookies".

    Matching is still per-attribute, so these are two labels over the one
    `cookies_text` field.
    """
    if reason.scope is not None:
        return COOKIE_LABELS[reason.scope]
    return attr_label(reason.attr)


@dataclass
class MatchResult:
    """Outcome of matching an entry against a query."""

    matched: bool
    reasons: list[MatchReason] = field(default_factory=list[MatchReason])


# When a term matches a "specific" field, drop matches on the "broader" fields
# it's known to be embedded in - they're the same substring, not a distinct hit.
_OVERLAP_RULES: dict[str, list[str]] = {
    "query_params_text": ["url", "req_headers_text", "res_headers_text"],
    "cookies_text": ["req_headers_text", "res_headers_text"],
    "url": ["req_headers_text"],
}


def dedupe_overlapping_reasons(reasons: list[MatchReason]) -> list[MatchReason]:
    """Drop reasons on a broader field when the same term already matched via
    a more specific field it's embedded in (e.g. a cookie value duplicated in
    its Cookie/Set-Cookie header line, or a query string duplicated in the URL)."""
    present_attrs = {r.attr for r in reasons}
    broad_attrs_to_drop: set[str] = set()
    for specific_attr, broad_attrs in _OVERLAP_RULES.items():
        if specific_attr in present_attrs:
            broad_attrs_to_drop.update(broad_attrs)
    if not broad_attrs_to_drop:
        return reasons
    return [r for r in reasons if r.attr not in broad_attrs_to_drop]


def _cookies_contain(
    cookies: Sequence[Mapping[str, object]],
    needle: str,
    fold_case: bool,
) -> bool:
    """Whether `needle` appears in any "name=value" pair of `cookies`."""
    for cookie in cookies:
        text = f"{cookie.get('name', '')}={cookie.get('value', '')}"
        if fold_case:
            text = text.lower()
        if needle in text:
            return True
    return False


def _scopes_for(
    entry: ParsedEntry,
    attr: str,
    needle: str,
    fold_case: bool,
) -> list[CookieScope | None]:
    """Sides to report for a hit on `attr`, one entry per reason to emit.

    Non-cookie fields yield a single scopeless hit. A cookie value sitting on
    both sides yields two - one per side - so a summary can union sides across
    entries without ending up with a composite label next to its own parts.

    [None] also covers a cookie hit on part of `cookies_text` that is neither a
    name nor a value (a Path or Expires attribute, say); the UI shows plain
    "Cookies" for those.
    """
    if attr != _COOKIE_ATTR:
        return [None]

    if fold_case:
        needle = needle.lower()
    sides: tuple[tuple[CookieScope, Sequence[Mapping[str, object]]], ...] = (
        ("sent", entry.req_cookies),
        ("received", entry.res_cookies),
    )
    matched: list[CookieScope | None] = [
        scope for scope, cookies in sides if _cookies_contain(cookies, needle, fold_case)
    ]
    return matched or [None]


@lru_cache(maxsize=512)
def _encode_variants_cached(value: str, encodings: tuple[str, ...]) -> dict[str, str]:
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


def encode_variants(value: str, encodings: set[str]) -> dict[str, str]:
    """Return {encoding_name: transformed_value} for each selected encoding/hash.

    Depends only on `value` and `encodings`, never on which entry is being
    checked - cached so a scan over many entries (Network Log's filter/highlight,
    which calls this once per entry) hashes each value once instead of once per
    entry.
    """
    if not value or not encodings:
        return {}
    return _encode_variants_cached(value, tuple(sorted(encodings)))


def collect_reasons(
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
            # The plain check folds case, so the scope lookup must too.
            for scope in _scopes_for(entry, attr, term, fold_case=True):
                reasons.append(MatchReason(term=term, attr=attr, encoding=None, scope=scope))
        for name, variant in variants.items():
            if variant in text:
                # Encoded forms are matched verbatim, so the scope lookup is too.
                for scope in _scopes_for(entry, attr, variant, fold_case=False):
                    reasons.append(MatchReason(term=term, attr=attr, encoding=name, scope=scope))
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

    # Route field-specific searches (e.g., url:google, cookies:sid).
    # Exclude normal http(s) protocols so direct URL searches don't break.
    field_name: str | None = None
    value = term
    if ":" in term and not term.startswith(("http:", "https:")):
        prefix, remainder = term.split(":", 1)
        if prefix.lower() in FIELD_MAP:
            field_name = prefix.lower()
            value = remainder

    if field_name is not None:
        reasons: list[MatchReason] = []
        if field_name == "status" and re.fullmatch(r"[1-5]xx", value.lower()):
            if entry.status.startswith(value[0]):
                reasons.append(MatchReason(term=value, attr="status", encoding=None))
        else:
            variants = encode_variants(value, encodings)
            reasons = collect_reasons(entry, FIELD_MAP[field_name], value, variants)
    else:
        # Default fallback standard search (includes an unrecognized field
        # prefix, e.g. "foo:bar" - searched as the literal string "foo:bar").
        attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
        variants = encode_variants(value, encodings)
        reasons = collect_reasons(entry, attrs, value, variants)
        reasons = dedupe_overlapping_reasons(reasons)

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
    method_reasons: list[MatchReason] = []
    if methods:
        if entry.method not in methods:
            return MatchResult(matched=False)
        method_reasons.append(MatchReason(term=entry.method, attr="method", encoding=None))

    if not query:
        return MatchResult(matched=True, reasons=method_reasons)

    try:
        terms = shlex.split(query)
    except ValueError:
        # Prevent app-crashes on incomplete/unclosed quote structures
        terms = query.split()

    active_encodings = encodings or set()
    all_reasons: list[MatchReason] = list(method_reasons)
    for term in terms:
        matched, reasons = match_term(entry, term, default_field, active_encodings)
        if not matched:
            return MatchResult(matched=False)
        all_reasons.extend(reasons)
    return MatchResult(matched=True, reasons=all_reasons)


def dissemination_badge_labels(reasons: list[MatchReason]) -> list[str]:
    """One label per distinct field a set of reasons hit, order-preserving --
    the compact chip form used wherever a row needs to show *why* it matched
    (Network Log's filter/highlight, Dissemination's value scan) without the
    per-encoding detail `summarize_reasons` spells out."""
    seen_labels: dict[str, None] = {}
    for reason in reasons:
        seen_labels.setdefault(reason_label(reason), None)
    return list(seen_labels)


def summarize_reasons(reasons: list[MatchReason]) -> str:
    """One entry per field, e.g. 'Response Headers (plain, MD5)' - collapses
    redundant links of the URL-encoding chain and lists other encodings once.

    Ported from the Streamlit app's ``tabs/networklog.py::_reason_summary``,
    made public here since both the Network Log and Dissemination endpoints
    need it.
    """
    by_attr: dict[str, list[str]] = {}
    for reason in reasons:
        label = reason_label(reason)
        form = reason.encoding or "plain"
        by_attr.setdefault(label, [])
        if form not in by_attr[label]:
            by_attr[label].append(form)

    parts: list[str] = []
    for label in sorted(by_attr):
        forms = dedupe_redundant_encodings(by_attr[label])
        forms_sorted = sorted(forms, key=lambda f: (f != "plain", f))
        parts.append(f"{label} ({', '.join(forms_sorted)})")
    return ", ".join(parts)
