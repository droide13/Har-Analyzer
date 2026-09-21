"""Overview tab logic: summary metrics, domain/subdomain aggregation, and
opt-in DNS + WHOIS resolution.

Ported from the Streamlit app's tabs/overview/overview.py. The pandas-based
``get_top_domains_df``/``build_subdomain_table_data`` helpers are dropped --
the frontend gets the full ``domain_map`` once and does its own
sort/limit/selection client-side (the map is tiny, bounded by distinct
domains rather than entries), so that server round trip per slider tweak
isn't needed here the way it is for Network Log's per-entry filtering.
"""

from dataclasses import dataclass
from typing import Any, TypedDict, cast

import dns.exception
import dns.resolver
from ipwhois import IPWhois  # pyright: ignore[reportMissingTypeStubs]

from app.core.models import ParsedEntry
from app.shared.naming import get_attrs_from_har_name


class SubdomainMetric(TypedDict):
    """Per-subdomain request count and total bandwidth.

    ``sized_requests`` is how many of those requests actually had a
    measurable body/headers size in the HAR (some entries -- redirects,
    cached responses, aborted/challenge responses -- report -1 for both,
    which is "unknown", not "zero"). The UI uses it to tell "0 bytes
    measured" apart from "no size data available" instead of showing a
    flat, misleading 0 B for both.
    """

    requests: int
    bytes: int
    sized_requests: int


class RootDomainMetric(TypedDict):
    """Aggregated traffic for one root domain, plus its per-subdomain breakdown."""

    requests: int
    bytes: int
    sized_requests: int
    subdomains: dict[str, SubdomainMetric]


class OverviewSummary(TypedDict):
    """Overall HAR capture summary stats."""

    total_requests: int
    total_bandwidth: int
    sized_requests: int
    unique_domains: int
    avg_latency_ms: float


@dataclass(slots=True)
class SubdomainResolutionRow:
    """One row of the full subdomain DNS resolution + WHOIS results table."""

    subdomain: str
    chain: str
    ips: str
    organization: str


def get_base_domain(domain: str) -> str:
    """Extracts the base/root domain (e.g. 'api.github.com' -> 'github.com')."""
    if not domain or domain == "unknown":
        return "unknown"

    parts = domain.lower().split(".")
    if len(parts) <= 2:
        return domain

    # Check for common multi-part suffixes (e.g., co.uk, com.br, gov.uk)
    if len(parts[-2]) <= 3 and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def get_first_party_domain(entries: list[ParsedEntry], filename: str | None = None) -> str:
    """First-party (site-owner) root domain for this capture.

    Prefers the domain embedded in the standardized filename -- via the same
    `get_attrs_from_har_name` convention used elsewhere in the app.
    Falls back to the root domain of the first entry with a resolvable domain.
    """
    if filename:
        attrs = get_attrs_from_har_name(filename)
        domain = attrs.get("domain") if attrs else None
        if domain:
            return get_base_domain(str(domain).lower())

    for entry in entries:
        if entry.domain and entry.domain != "unknown":
            return get_base_domain(entry.domain)
    return "unknown"


def _has_measured_size(entry: ParsedEntry) -> bool:
    """Whether the HAR actually reported a size for this entry, as opposed
    to the -1 "unknown" sentinel (redirects, cached/challenge responses)."""
    return entry.body_size >= 0 or entry.headers_size >= 0


def calculate_overview_summary(entries: list[ParsedEntry]) -> OverviewSummary:
    """Calculates top-level summary metrics for requests, size, domains, and latency."""
    total = len(entries)
    # Treat negative sizes (-1 from cache/unknown) as 0
    bandwidth = sum(max(0, e.body_size) + max(0, e.headers_size) for e in entries)
    sized_requests = sum(1 for e in entries if _has_measured_size(e))
    domains = len({e.domain for e in entries if e.domain})
    avg_latency = (sum(e.time_ms for e in entries) / total) if total > 0 else 0.0

    return {
        "total_requests": total,
        "total_bandwidth": bandwidth,
        "sized_requests": sized_requests,
        "unique_domains": domains,
        "avg_latency_ms": avg_latency,
    }


def get_method_counts(entries: list[ParsedEntry]) -> dict[str, int]:
    """Calculates HTTP request distribution grouped by HTTP method."""
    m_data: dict[str, int] = {}
    for e in entries:
        m_data[e.method] = m_data.get(e.method, 0) + 1
    return m_data


def get_status_counts(entries: list[ParsedEntry]) -> dict[str, int]:
    """Calculates HTTP response distribution grouped by status code."""
    s_data: dict[str, int] = {}
    for e in entries:
        key = str(e.status) if e.status else "Incomplete"
        s_data[key] = s_data.get(key, 0) + 1
    return s_data


def build_domain_map(entries: list[ParsedEntry]) -> dict[str, RootDomainMetric]:
    """Aggregates request counts and byte sizes by root domain and subdomain."""
    domain_map: dict[str, RootDomainMetric] = {}

    for e in entries:
        domain = e.domain.lower() if e.domain else "unknown"
        base = get_base_domain(domain)
        size = max(0, e.body_size) + max(0, e.headers_size)
        sized = 1 if _has_measured_size(e) else 0

        if base not in domain_map:
            domain_map[base] = {"requests": 0, "bytes": 0, "sized_requests": 0, "subdomains": {}}

        domain_map[base]["requests"] += 1
        domain_map[base]["bytes"] += size
        domain_map[base]["sized_requests"] += sized

        if domain not in domain_map[base]["subdomains"]:
            domain_map[base]["subdomains"][domain] = {
                "requests": 0,
                "bytes": 0,
                "sized_requests": 0,
            }

        domain_map[base]["subdomains"][domain]["requests"] += 1
        domain_map[base]["subdomains"][domain]["bytes"] += size
        domain_map[base]["subdomains"][domain]["sized_requests"] += sized

    return domain_map


def _resolve_cname_chain(name: str, max_hops: int = 10) -> tuple[list[str], list[str]]:
    """Follow CNAME records until an A/AAAA record is found."""
    chain = [name]
    current = name
    for _ in range(max_hops):
        try:
            answer = cast(Any, dns.resolver.resolve(current, "CNAME"))
            target = str(answer[0].target).rstrip(".")
        except dns.resolver.NoAnswer:
            break
        except dns.resolver.NXDOMAIN:
            return chain, []
        except dns.exception.DNSException:
            break
        if target in chain:
            break  # CNAME loop guard
        chain.append(target)
        current = target

    ips: list[str] = []
    for rdtype in ("A", "AAAA"):
        try:
            answer = cast(Any, dns.resolver.resolve(current, rdtype))
            ips.extend(str(record) for record in answer)
        except dns.exception.DNSException:
            continue
    return chain, ips


def _whois_org_for_ip(ip: str) -> str:
    """Look up network owner organization for an IP via RDAP."""
    try:
        ipwhois_obj = cast(Any, IPWhois(ip))
        result = cast(dict[str, Any], ipwhois_obj.lookup_rdap(depth=1))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return f"(WHOIS lookup failed: {exc})"

    network = cast(dict[str, Any], result.get("network") or {})
    org = network.get("name") or result.get("asn_description") or "Unknown"
    return str(org)


def resolve_subdomains(subdomains: list[str]) -> list[SubdomainResolutionRow]:
    """Fully resolve each subdomain (CNAME chain -> IP -> WHOIS).

    Uncached here (unlike the original's ``@st.cache_data``): each call is an
    explicit, opt-in POST triggered by the frontend's "Resolve subdomains"
    button, so there's no rerun to guard against re-triggering it for free.
    """
    rows: list[SubdomainResolutionRow] = []
    for sub in subdomains:
        chain, ips = _resolve_cname_chain(sub)
        org = _whois_org_for_ip(ips[0]) if ips else "N/A (no IP resolved)"
        rows.append(
            SubdomainResolutionRow(
                subdomain=sub,
                chain=" -> ".join(chain),
                ips=", ".join(ips) if ips else "(unresolved)",
                organization=org,
            )
        )
    return rows
