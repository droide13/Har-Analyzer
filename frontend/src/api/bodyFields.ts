/** Typed calls against backend/app/routers/body_fields.py. */

import { apiGet } from './client'
import type { RecordsView } from './types'

export function fetchBodyFields(uploadId: string): Promise<RecordsView> {
  return apiGet<RecordsView>(`/api/har/${uploadId}/body-fields`)
}
