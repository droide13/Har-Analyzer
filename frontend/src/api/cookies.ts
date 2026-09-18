/** Typed calls against backend/app/routers/cookies.py. */

import { apiGet } from './client'
import type { RecordsView } from './types'

export function fetchCookies(uploadId: string): Promise<RecordsView> {
  return apiGet<RecordsView>(`/api/har/${uploadId}/cookies`)
}
