/** Typed calls against backend/app/routers/har.py. */

import { apiGet, apiPostForm } from './client'
import type { EntriesPage, EntryDetail, ScopeOptions, UploadResponse } from './types'

export function uploadHar(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiPostForm<UploadResponse>('/api/har/upload', form)
}

export interface EntriesQuery {
  q?: string
  h?: string
  scope?: string
  methods?: string[]
  /** Omit entirely for "all encodings" (the backend's default); pass [] for "none". */
  encodings?: string[]
  /** Ground-truth keys to check for (see the file's own log._analysis.ground_truth).
   * Omit entirely for "all tagged keys" (the backend's default); pass [] for "none". */
  gtKeys?: string[]
  page: number
  page_size: number
}

export function fetchEntries(uploadId: string, query: EntriesQuery): Promise<EntriesPage> {
  return apiGet<EntriesPage>(`/api/har/${uploadId}/entries`, {
    q: query.q || undefined,
    h: query.h || undefined,
    scope: query.scope,
    methods: query.methods?.length ? query.methods.join(',') : undefined,
    encodings: query.encodings === undefined ? undefined : query.encodings.join(','),
    gt_keys: query.gtKeys === undefined ? undefined : query.gtKeys.join(','),
    page: query.page,
    page_size: query.page_size,
  })
}

export function fetchEntryDetail(uploadId: string, index: number): Promise<EntryDetail> {
  return apiGet<EntryDetail>(`/api/har/${uploadId}/entries/${index}`)
}

export function fetchMethodOrder(): Promise<string[]> {
  return apiGet<string[]>('/api/har/meta/methods')
}

export function fetchEncodingOptions(): Promise<string[]> {
  return apiGet<string[]>('/api/har/meta/encodings')
}

export function fetchScopeOptions(): Promise<ScopeOptions> {
  return apiGet<ScopeOptions>('/api/har/meta/scopes')
}
