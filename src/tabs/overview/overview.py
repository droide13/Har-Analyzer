"""Data processing and logic layer for the Overview / HAR Analytics panel."""

from typing import Any, Callable, TypedDict, cast

import dns.exception
import dns.resolver
import pandas as pd
import streamlit as st
from ipwhois import IPWhois  # pyright: ignore[reportMissingTypeStubs]

from core.models import ParsedEntry
from tabs.naming.naming import get_attrs_from_har_name

# --- Data Models / Type Definitions ---


class SubdomainMetric(TypedDict):
    """Per-subdomain request count and total bandwidth."""

    requests: int
    bytes: int


class RootDomainMetric(TypedDict):
    """Aggregated traffic for one root domain, plus its per-subdomain breakdown."""

    requests: int
    bytes: int
    subdomains: dict[str, SubdomainMetric]


class SubdomainRow(TypedDict):
    """One row of the subdomain breakdown table."""

    Subdomain: str
    Requests: int
    Bytes: int
    Size: str


class SubdomainResolutionRow(TypedDict):
    """One row of the full subdomain DNS resolution + WHOIS results table."""

    Subdomain: str
    Chain: str
    IPs: str
    Organization: str


class OverviewSummary(TypedDict):
    """Overall HAR capture summary stats."""

    total_requests: int
    total_bandwidth: int
    unique_domains: int
    avg_latency_ms: float


# --- Domain Extraction Helpers ---


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


# --- Aggregation Logic ---


def calculate_overview_summary(entries: list[ParsedEntry]) -> OverviewSummary:
    """Calculates top-level summary metrics for requests, size, domains, and latency."""
    total = len(entries)
    # Treat negative sizes (-1 from cache/unknown) as 0
    bandwidth = sum(max(0, e.body_size) + max(0, e.headers_size) for e in entries)
    domains = len({e.domain for e in entries if e.domain})
    avg_latency = (sum(e.time_ms for e in entries) / total) if total > 0 else 0.0

    return {
        "total_requests": total,
        "total_bandwidth": bandwidth,
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

        if base not in domain_map:
            domain_map[base] = {"requests": 0, "bytes": 0, "subdomains": {}}

        domain_map[base]["requests"] += 1
        domain_map[base]["bytes"] += size

        if domain not in domain_map[base]["subdomains"]:
            domain_map[base]["subdomains"][domain] = {"requests": 0, "bytes": 0}

        domain_map[base]["subdomains"][domain]["requests"] += 1
        domain_map[base]["subdomains"][domain]["bytes"] += size

    return domain_map


def get_top_domains_df(
    domain_map: dict[str, RootDomainMetric], sort_by: str, limit: int
) -> pd.DataFrame:
    """Creates a pandas DataFrame of top domains according to sorting and limit rules."""

    def _root_sort_key(item: tuple[str, RootDomainMetric]) -> int:
        return item[1]["requests"] if sort_by == "Requests" else item[1]["bytes"]

    sorted_domains = sorted(domain_map.items(), key=_root_sort_key, reverse=True)

    return pd.DataFrame(
        [
            {
                "Domain": d[0],
                "Value": d[1]["requests"] if sort_by == "Requests" else d[1]["bytes"],
            }
            for d in sorted_domains[:limit]
        ]
    )


def build_subdomain_table_data(
    root_metric: RootDomainMetric,
    sort_by: str,
    bytes_formatter: Callable[[int], str],
) -> list[SubdomainRow]:
    """Builds and sorts the subdomain metric rows for display."""
    sub_table_data: list[SubdomainRow] = []

    for sub, metrics in root_metric["subdomains"].items():
        sub_table_data.append(
            {
                "Subdomain": sub,
                "Requests": metrics["requests"],
                "Bytes": metrics["bytes"],
                "Size": bytes_formatter(metrics["bytes"]),
            }
        )

    def _sub_sort_key(r: SubdomainRow) -> int:
        return r["Requests"] if sort_by == "Requests" else r["Bytes"]

    sub_table_data.sort(key=_sub_sort_key, reverse=True)
    return sub_table_data


# --- DNS & WHOIS Resolution Logic ---


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


@st.cache_data(show_spinner=False)
def resolve_subdomains(subdomains: tuple[str, ...]) -> list[SubdomainResolutionRow]:
    """Fully resolve each subdomain (CNAME chain -> IP -> WHOIS)."""
    rows: list[SubdomainResolutionRow] = []
    for sub in subdomains:
        chain, ips = _resolve_cname_chain(sub)
        org = _whois_org_for_ip(ips[0]) if ips else "N/A (no IP resolved)"
        rows.append(
            {
                "Subdomain": sub,
                "Chain": " -> ".join(chain),
                "IPs": ", ".join(ips) if ips else "(unresolved)",
                "Organization": org,
            }
        )
    return rows
