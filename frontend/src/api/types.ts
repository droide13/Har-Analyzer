/**
 * Mirrors backend/app/schemas.py field-for-field. Keep these two files in
 * sync by hand -- there are only a handful of shapes, not worth codegen for.
 */

export interface SessionMetadata {
  domain: string
  platform: string | null
  interaction: string | null
  cookies: string | null
  visit: string | null
  extra: string | null
  captured_at: string | null
  filename_valid: boolean
  has_analysis: boolean
}

export interface UploadResponse {
  upload_id: string
  filename: string
  entry_count: number
  session_metadata: SessionMetadata
}

/** One field a badge's reasons hit, structured rather than just formatted
 * into the badge's label -- `attr` is a ParsedEntry attribute name (see
 * backend/app/shared/search.py's ATTR_LABELS), used to route a click to the
 * matching entry-detail tab; `text` is the literal substring that matched,
 * for highlighting there. */
export interface BadgeFieldMatch {
  attr: string
  label: string
  text: string
}

export interface EntryBadge {
  label: string
  tone: 'neutral' | 'orange'
  matches: BadgeFieldMatch[]
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
  highlighted: boolean
  badges: EntryBadge[]
}

export interface EntriesPage {
  total: number
  filtered: number
  highlighted: number
  page: number
  page_size: number
  total_pages: number
  items: EntrySummary[]
  highlighted_pages: number[]
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
  /** Original, unmodified HAR entry JSON -- backs the Timing/Details tabs. */
  raw: Record<string, unknown>
}

/** label -> field-key map, e.g. { "All fields": "any", URL: "url", ... }. */
export type ScopeOptions = Record<string, string>

// --- Overview ---

export interface OverviewSummary {
  total_requests: number
  total_bandwidth: number
  sized_requests: number
  unique_domains: number
  avg_latency_ms: number
}

export interface SubdomainMetric {
  requests: number
  bytes: number
  sized_requests: number
}

export interface RootDomainMetric {
  requests: number
  bytes: number
  sized_requests: number
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

// --- Dissemination ---

export interface DisseminationFirstSeen {
  origin: string
  when: string
  method: string
  domain: string
  value: string
}

export interface InitiatorChainLink {
  found: boolean
  entry: EntrySummary | null
  url: string
  initiator_type: string
}

export interface DisseminationTimelineResponse {
  sightings: number
  distinct_values: number
  origins: string[]
  first_seen: DisseminationFirstSeen
  initiator_chain: InitiatorChainLink[]
  timeline: Record<string, unknown>[]
}

export interface DisseminationMatchRow {
  entry: EntrySummary
  reasons: { Field: string; Value: string; Forms: string }[]
}

export interface DisseminationSearchResponse {
  by_domain: Record<string, unknown>[]
  matches: DisseminationMatchRow[]
}

// --- Metadata ---

export interface HarAnalysis {
  tool_version: string
  domain: string
  platform: string
  interact: string
  cookies: string
  visit: string
  extra: string
  captured_at: string
  standardized_filename: string
  description: string
  email_used: string
  notes: string
}

export interface MetadataDetected {
  first_request_domain: string
  captured_at: string | null
  domain_options: string[]
}

export interface MetadataResponse {
  detected: MetadataDetected
  existing_analysis: HarAnalysis | null
}

export interface GenerateMetadataRequest {
  domain: string
  platform: string
  interact: string
  cookies: string
  visit: string
  extra?: string
  captured_at: string
  description?: string
  email_used?: string
  notes?: string
}

export interface GenerateMetadataResponse {
  filename: string
  analysis: HarAnalysis
}

/** internal-code -> display-label maps, e.g. { login: "Login" }. */
export interface NamingOptions {
  platform: Record<string, string>
  interact: Record<string, string>
  cookies: Record<string, string>
  visit: Record<string, string>
}
