/** Typed calls against backend/app/routers/identifiers.py. */

import { apiGet } from './client'
import type { IdentifiersResponse } from './types'

export interface IdentifiersQuery {
  min_appearances: number
  max_unique_values: number
  min_avg_length: number
  min_avg_entropy: number
  name_query: string
  exclude_common: boolean
  sort_by: string
}

export function fetchIdentifiers(uploadId: string, query: IdentifiersQuery): Promise<IdentifiersResponse> {
  return apiGet<IdentifiersResponse>(`/api/har/${uploadId}/identifiers`, {
    ...query,
    exclude_common: String(query.exclude_common),
  })
}
