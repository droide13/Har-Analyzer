/** Typed calls against backend/app/routers/overview.py. */

import { apiGet, apiPostJson } from './client'
import type { OverviewResponse, SubdomainResolutionRow } from './types'

export function fetchOverview(uploadId: string): Promise<OverviewResponse> {
  return apiGet<OverviewResponse>(`/api/har/${uploadId}/overview`)
}

export function resolveSubdomains(uploadId: string, subdomains: string[]): Promise<SubdomainResolutionRow[]> {
  return apiPostJson<SubdomainResolutionRow[]>(`/api/har/${uploadId}/overview/resolve-subdomains`, { subdomains })
}
