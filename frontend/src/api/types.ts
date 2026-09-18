/**
 * Mirrors backend/app/schemas.py field-for-field. Keep these two files in
 * sync by hand -- there are only a handful of shapes, not worth codegen for.
 */

export interface UploadResponse {
  upload_id: string
  filename: string
  entry_count: number
}

export interface EntrySummary {
  index: number
  started_date_time: string
  method: string
  url: string
  domain: string
  status: string
  status_text: string
  mime: string
  time_ms: number
  body_size: number
  req_cookie_count: number
  res_cookie_count: number
  filter_summary: string | null
  highlighted: boolean
  highlight_summary: string | null
}

export interface EntriesPage {
  total: number
  filtered: number
  highlighted: number
  page: number
  page_size: number
  total_pages: number
  items: EntrySummary[]
}

export interface HeaderPair {
  name: string
  value: string
}

export interface EntryDetail {
  index: number
  started_date_time: string
  method: string
  url: string
  domain: string
  status: string
  status_text: string
  mime: string
  time_ms: number
  body_size: number
  headers_size: number
  req_headers: HeaderPair[]
  res_headers: HeaderPair[]
  query_params: HeaderPair[]
  req_cookies: Record<string, unknown>[]
  res_cookies: Record<string, unknown>[]
  req_body: string
  res_body: string
  initiator_type: string
  initiator_url: string
  initiator_stack: Record<string, unknown>[]
}

/** label -> field-key map, e.g. { "All fields": "any", URL: "url", ... }. */
export type ScopeOptions = Record<string, string>

// --- Overview ---

export interface OverviewSummary {
  total_requests: number
  total_bandwidth: number
  unique_domains: number
  avg_latency_ms: number
}

export interface SubdomainMetric {
  requests: number
  bytes: number
}

export interface RootDomainMetric {
  requests: number
  bytes: number
  subdomains: Record<string, SubdomainMetric>
}

export interface OverviewResponse {
  summary: OverviewSummary
  method_counts: Record<string, number>
  status_counts: Record<string, number>
  domain_map: Record<string, RootDomainMetric>
  first_party_domain: string
}

export interface SubdomainResolutionRow {
  subdomain: string
  chain: string
  ips: string
  organization: string
}

// --- Cookies / Query Params (identical shape) ---

export interface RecordsView {
  metrics: Record<string, number>
  records: Record<string, unknown>[]
  aggregated: Record<string, unknown>[]
}

// --- Identifiers ---

export interface IdentifierValueRow {
  value: string
  first_seen_as: string | null
  appearances: number
  length: number
  entropy: number
  domains: string
}

export interface IdentifierSummaryRow {
  key: string
  first_seen_as: string | null
  appearances: number
  unique_values: number
  avg_length: number
  avg_entropy: number
  domains: string
  values: IdentifierValueRow[]
}

export interface IdentifiersResponse {
  query_params: IdentifierSummaryRow[]
  cookies: IdentifierSummaryRow[]
}
