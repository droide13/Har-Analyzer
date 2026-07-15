"""HAR searching, tokenizing, and matching execution engine."""

import re
import shlex
from models import ParsedEntry, FIELD_MAP

def match_term(entry: ParsedEntry, term: str, default_field: str) -> bool:
    is_negated = False
    # Identify and isolate negated query markers (e.g., -status:200)
    if term.startswith("-") and len(term) > 1:
        is_negated = True
        term = term[1:]

    term = term.strip("'\"")
    matched = False

    # Route field-specific searches (e.g., url:google, cookies:sid)
    # Exclude normal http(s) protocols so direct URL searches don't break
    if ":" in term and not term.startswith(("http:", "https:")):
        field, value = term.split(":", 1)
        field = field.lower()
        
        if field in FIELD_MAP:
            if field == "status" and re.fullmatch(r"[1-5]xx", value.lower()):
                matched = entry.status.startswith(value[0])
            else:
                attrs = FIELD_MAP[field]
                matched = any(value.lower() in str(getattr(entry, attr)).lower() for attr in attrs)
        else:
            attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
            matched = any(term.lower() in str(getattr(entry, attr)).lower() for attr in attrs)
    else:
        # Default fallback standard search
        attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
        matched = any(term.lower() in str(getattr(entry, attr)).lower() for attr in attrs)

    return not matched if is_negated else matched


def entry_matches(entry: ParsedEntry, query: str, default_field: str, methods: set[str]) -> bool:
    """Evaluate whether an entry satisfies selected methods and tokenized search terms."""
    if methods and entry.method not in methods:
        return False
    if not query:
        return True
    try:
        terms = shlex.split(query)
    except ValueError:
        # Prevent app-crashes on incomplete/unclosed quote structures
        terms = query.split()
    return all(match_term(entry, term, default_field) for term in terms)