/** Typed calls against backend/app/routers/query_params.py. */

import { apiGet } from './client'
import type { RecordsView } from './types'

export function fetchQueryParams(uploadId: string): Promise<RecordsView> {
  return apiGet<RecordsView>(`/api/har/${uploadId}/query-params`)
}
