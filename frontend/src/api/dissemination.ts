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
  /** Ground-truth keys to check for; omit entirely to skip the check (it's
   * a full scan, opt-in only), pass [] to run it with none included. */
  gtKeys?: string[]
}

export function searchDissemination(uploadId: string, query: DisseminationSearchQuery): Promise<DisseminationSearchResponse> {
  return apiPostJson<DisseminationSearchResponse>(`/api/har/${uploadId}/dissemination/search`, {
    key: query.key,
    encodings: query.encodings,
    narrow: query.narrow,
    highlight: query.highlight,
    gt_keys: query.gtKeys,
  })
}
