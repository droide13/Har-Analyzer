"""Overview tab endpoints: summary metrics/domain map in one call, plus an
opt-in DNS/WHOIS subdomain resolution endpoint."""

from fastapi import APIRouter, HTTPException

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
from app.store import UploadNotFoundError, upload_store

router = APIRouter(prefix="/api/har", tags=["overview"])


@router.get("/{upload_id}/overview", response_model=OverviewResponse)
async def get_overview(upload_id: str) -> OverviewResponse:
    """Summary metrics, method/status distribution, and the domain map."""
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

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
    lookup -- slow and network-bound, so it's only ever called on an explicit
    "Resolve subdomains" click, never automatically."""
    try:
        upload_store.get(upload_id)  # validate the id exists; entries aren't needed here
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    rows = resolve_subdomains(sorted(set(body.subdomains)))
    return [
        SubdomainResolutionRow(
            subdomain=r.subdomain, chain=r.chain, ips=r.ips, organization=r.organization
        )
        for r in rows
    ]
