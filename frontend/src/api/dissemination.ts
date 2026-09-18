/** Typed calls against backend/app/routers/dissemination.py. */

import { apiGet, apiPostJson } from './client'
import type { DisseminationSearchResponse, DisseminationTimelineResponse } from './types'

export function fetchDisseminationKeys(uploadId: string): Promise<string[]> {
  return apiGet<string[]>(`/api/har/${uploadId}/dissemination/keys`)
}

export function fetchDisseminationTimeline(uploadId: string, key: string): Promise<DisseminationTimelineResponse> {
  return apiGet<DisseminationTimelineResponse>(`/api/har/${uploadId}/dissemination/timeline`, { key })
}

export interface DisseminationSearchQuery {
  key: string
  encodings: string[]
  narrow?: string
  highlight?: string
}

export function searchDissemination(uploadId: string, query: DisseminationSearchQuery): Promise<DisseminationSearchResponse> {
  return apiPostJson<DisseminationSearchResponse>(`/api/har/${uploadId}/dissemination/search`, query)
}
