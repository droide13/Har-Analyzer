/** Typed calls against backend/app/routers/metadata.py and routers/naming.py. */

import { apiGet, apiPostJson } from './client'
import type { GenerateMetadataRequest, GenerateMetadataResponse, MetadataResponse, NamingOptions } from './types'

export function fetchMetadata(uploadId: string): Promise<MetadataResponse> {
  return apiGet<MetadataResponse>(`/api/har/${uploadId}/metadata`)
}

export function generateMetadata(uploadId: string, body: GenerateMetadataRequest): Promise<GenerateMetadataResponse> {
  return apiPostJson<GenerateMetadataResponse>(`/api/har/${uploadId}/metadata/generate`, body)
}

/** The download endpoint isn't fetched as JSON -- see triggerDownload in
 * MetadataView, which just navigates the browser to this URL. */
export function standardizedDownloadUrl(uploadId: string): string {
  return `/api/har/${uploadId}/metadata/download`
}

export function fetchNamingOptions(): Promise<NamingOptions> {
  return apiGet<NamingOptions>('/api/naming/options')
}
