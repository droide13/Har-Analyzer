"""Overview tab endpoints: summary metrics/domain map in one call, plus an
opt-in DNS/WHOIS subdomain resolution endpoint."""

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.features.overview import (
    build_domain_map,
    calculate_overview_summary,
    get_first_party_domain,
    get_method_counts,
    get_status_counts,
    resolve_subdomains,
)
from app.schemas import (
    OverviewResponse,
    ResolveSubdomainsRequest,
    SubdomainResolutionRow,
)

from ._common import get_record_or_404

router = APIRouter(prefix="/api/har", tags=["overview"])


@router.get("/{upload_id}/overview", response_model=OverviewResponse)
async def get_overview(upload_id: str) -> OverviewResponse:
    """Summary metrics, method/status distribution, and the domain map."""
    record = get_record_or_404(upload_id)

    entries = record.entries
    return OverviewResponse(
        summary=calculate_overview_summary(entries),
        method_counts=get_method_counts(entries),
        status_counts=get_status_counts(entries),
        domain_map=build_domain_map(entries),
        first_party_domain=get_first_party_domain(entries, record.filename),
    )


@router.post(
    "/{upload_id}/overview/resolve-subdomains", response_model=list[SubdomainResolutionRow]
)
async def post_resolve_subdomains(
    upload_id: str, body: ResolveSubdomainsRequest
) -> list[SubdomainResolutionRow]:
    """Follows each subdomain's CNAME chain to an IP, then a WHOIS/RDAP owner
    lookup -- slow, network-bound, and synchronous, so it's run in a
    threadpool (otherwise it would block the whole event loop, including
    every other concurrent request, for the entire lookup) and only ever
    called on an explicit "Resolve subdomains" click, never automatically."""
    get_record_or_404(upload_id)  # validate the id exists; entries aren't needed here

    rows = await run_in_threadpool(resolve_subdomains, sorted(set(body.subdomains)))
    return [
        SubdomainResolutionRow(
            subdomain=r.subdomain, chain=r.chain, ips=r.ips, organization=r.organization
        )
        for r in rows
    ]
