import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchBodyFields } from '../../api/bodyFields'
import { fetchCookies } from '../../api/cookies'
import { fetchIdentifiers } from '../../api/identifiers'
import { fetchQueryParams } from '../../api/queryParams'
import { AggregateToggleView } from '../../components/AggregateToggleView'
import type { DataTableColumn } from '../../components/DataTable'
import { Disclosure } from '../../components/Disclosure'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { HelpText } from '../../components/HelpText'
import { ErrorState, LoadingState } from '../../components/QueryState'
import { RangeField } from '../../components/RangeField'
import { SegmentedControl } from '../../components/SegmentedControl'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import type { IdentifiersResponse } from '../../api/types'
import { IdentifiersSection } from './IdentifiersSection'

interface IdentifiersViewProps {
  uploadId: string
  /** Wires up each key's "Trace" button -- jumps to the Dissemination tab
   * with that key pre-selected. Only reachable in identifier-filter mode --
   * "Show all" mode has no single value to trace, same as the old Cookies/
   * Query Params tabs never had one. */
  onTraceKey?: (key: string) => void
}

type Source = 'cookies' | 'query-params' | 'body-fields' | 'known-ids'

/** Known IDs is an exact-name lookup against studied vendors, not a
 * heuristic -- it has no entropy/cardinality filter sliders and no raw
 * "Show all" superset, unlike the other three sources. It gets its own
 * view component below rather than threading conditionals through the
 * shared filtered view. */
type RecordsSource = Exclude<Source, 'known-ids'>

const SOURCE_OPTIONS = [
  { value: 'known-ids', label: 'Known IDs' },
  { value: 'cookies', label: 'Cookies' },
  { value: 'query-params', label: 'Query Parameters' },
  { value: 'body-fields', label: 'Body Fields' },
]

const SOURCE_LABELS: Record<RecordsSource, string> = {
  cookies: 'Cookies',
  'query-params': 'Query Parameters',
  'body-fields': 'Body Fields',
}

const SOURCE_DATA_KEY: Record<RecordsSource, keyof IdentifiersResponse> = {
  cookies: 'cookies',
  'query-params': 'query_params',
  'body-fields': 'body_fields',
}

const SORT_OPTIONS = ['Appearances', 'Entropy', 'Avg length', 'Unique values'] as const

/** Shapes of the plain dict rows backend/app/features/cookies.py and
 * query_params.py return -- documented here rather than typed at the API
 * layer, since the backend response is intentionally a loose dict (see
 * RecordsView). */
interface CookieRecord {
  Name: string
  Value: string
  Scope: string
  Secure: boolean
  HttpOnly: boolean
  Host: string
}

interface CookieAggregate {
  Name: string
  'First Seen As': string
  Scope: string
  Secure: string
  HttpOnly: string
  Value: string
  Occurrences: number
  Hosts: string
}

interface QueryParamRecord {
  Name: string
  Value: string
  Method: string
  Host: string
}

interface QueryParamAggregate {
  Name: string
  Method: string
  Value: string
  Occurrences: number
  Hosts: string
}

interface BodyFieldRecord {
  Name: string
  Value: string
  Scope: string
  Host: string
}

interface BodyFieldAggregate {
  Name: string
  Scope: string
  Value: string
  Occurrences: number
  Hosts: string
}

const COOKIE_AGGREGATED_COLUMNS: DataTableColumn<CookieAggregate>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'First Seen As', accessor: (r) => r['First Seen As'] },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Secure', accessor: (r) => r.Secure },
  { header: 'HttpOnly', accessor: (r) => r.HttpOnly },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Occurrences', accessor: (r) => r.Occurrences },
  { header: 'Hosts', accessor: (r) => r.Hosts },
]

const COOKIE_RAW_COLUMNS: DataTableColumn<CookieRecord>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Secure', accessor: (r) => String(r.Secure) },
  { header: 'HttpOnly', accessor: (r) => String(r.HttpOnly) },
  { header: 'Host', accessor: (r) => r.Host },
]

const QUERY_PARAM_AGGREGATED_COLUMNS: DataTableColumn<QueryParamAggregate>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Method', accessor: (r) => r.Method },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Occurrences', accessor: (r) => r.Occurrences },
  { header: 'Hosts', accessor: (r) => r.Hosts },
]

const QUERY_PARAM_RAW_COLUMNS: DataTableColumn<QueryParamRecord>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Method', accessor: (r) => r.Method },
  { header: 'Host', accessor: (r) => r.Host },
]

const BODY_FIELD_AGGREGATED_COLUMNS: DataTableColumn<BodyFieldAggregate>[] = [
  { header: 'Name', accessor: (r) => r.Name, className: 'font-mono text-xs' },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Occurrences', accessor: (r) => r.Occurrences },
  { header: 'Hosts', accessor: (r) => r.Hosts },
]

const BODY_FIELD_RAW_COLUMNS: DataTableColumn<BodyFieldRecord>[] = [
  { header: 'Name', accessor: (r) => r.Name, className: 'font-mono text-xs' },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Host', accessor: (r) => r.Host },
]

/** The "Search key name" + "Sort by" pair, shared by FilteredIdentifiersView
 * and KnownIdsView -- identical shape, differing only in placeholder text
 * and whether disabled while "Show all" is on. */
function NameAndSortFields({
  nameQuery,
  onNameQueryChange,
  namePlaceholder,
  sortBy,
  onSortByChange,
  disabled,
}: {
  nameQuery: string
  onNameQueryChange: (value: string) => void
  namePlaceholder: string
  sortBy: (typeof SORT_OPTIONS)[number]
  onSortByChange: (value: (typeof SORT_OPTIONS)[number]) => void
  disabled?: boolean
}) {
  return (
    <>
      <FormField label="Search key name">
        <input
          type="text"
          className={fieldInputClasses}
          value={nameQuery}
          onChange={(e) => onNameQueryChange(e.target.value)}
          placeholder={namePlaceholder}
          disabled={disabled}
        />
      </FormField>
      <FormField label="Sort by">
        <select
          className={fieldInputClasses}
          value={sortBy}
          onChange={(e) => onSortByChange(e.target.value as (typeof SORT_OPTIONS)[number])}
          disabled={disabled}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </FormField>
    </>
  )
}

/** "Show all" mode: the full raw/aggregate listing for one source, unfiltered
 * -- what the old standalone Cookies/Query Params tabs showed. */
const EMPTY_RECORDS_LABEL: Record<RecordsSource, string> = {
  cookies: 'No cookies found.',
  'query-params': 'No query string parameters found.',
  'body-fields': 'No JSON body fields found.',
}

function AllRecordsView({ uploadId, source }: { uploadId: string; source: RecordsSource }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['all-records', uploadId, source],
    queryFn: () => {
      if (source === 'cookies') return fetchCookies(uploadId)
      if (source === 'query-params') return fetchQueryParams(uploadId)
      return fetchBodyFields(uploadId)
    },
    placeholderData: (previous) => previous,
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState label="Failed to load records." />

  if (data.records.length === 0) {
    return <p>{EMPTY_RECORDS_LABEL[source]}</p>
  }

  if (source === 'cookies') {
    return (
      <AggregateToggleView<CookieRecord, CookieAggregate>
        title="Cookies list"
        metrics={[
          { label: 'Total Cookies', value: data.metrics.total },
          { label: 'Insecure SSL Cookies', value: data.metrics.missing_secure },
          { label: 'Missing HttpOnly Protection', value: data.metrics.missing_http_only },
        ]}
        aggregatedCaption="One row per cookie name. Secure/HttpOnly show 'Mixed' if they vary across occurrences; Value shows the shared value or how many distinct values were seen."
        aggregatedColumns={COOKIE_AGGREGATED_COLUMNS}
        rawColumns={COOKIE_RAW_COLUMNS}
        records={data.records as unknown as CookieRecord[]}
        aggregated={data.aggregated as unknown as CookieAggregate[]}
      />
    )
  }

  if (source === 'query-params') {
    return (
      <AggregateToggleView<QueryParamRecord, QueryParamAggregate>
        title="Query Parameters list"
        metrics={[
          { label: 'Total Params', value: data.metrics.total },
          { label: 'Unique Param Names', value: data.metrics.unique_names },
          { label: 'Empty Values', value: data.metrics.empty_values },
        ]}
        aggregatedCaption="One row per param name. Method lists every HTTP method the param appeared under; Value shows the shared value or how many distinct values were seen."
        aggregatedColumns={QUERY_PARAM_AGGREGATED_COLUMNS}
        rawColumns={QUERY_PARAM_RAW_COLUMNS}
        records={data.records as unknown as QueryParamRecord[]}
        aggregated={data.aggregated as unknown as QueryParamAggregate[]}
      />
    )
  }

  return (
    <AggregateToggleView<BodyFieldRecord, BodyFieldAggregate>
      title="Body Fields list"
      metrics={[
        { label: 'Total Fields', value: data.metrics.total },
        { label: 'Unique Field Paths', value: data.metrics.unique_paths },
        { label: 'Unique Hosts', value: data.metrics.unique_hosts },
      ]}
      aggregatedCaption="One row per JSON field path (flattened out of nested objects/arrays, e.g. fms_params.fms_uid2). Scope lists Request/Response body; Value shows the shared value or how many distinct values were seen."
      aggregatedColumns={BODY_FIELD_AGGREGATED_COLUMNS}
      rawColumns={BODY_FIELD_RAW_COLUMNS}
      records={data.records as unknown as BodyFieldRecord[]}
      aggregated={data.aggregated as unknown as BodyFieldAggregate[]}
    />
  )
}

/** Cookies, Query Params, and Body Fields: the shared entropy-filtered view,
 * with a "Show all" kill switch that either applies the 4-signal identifier
 * filter (sliders stay pinned above the table either way) or bypasses it
 * entirely for the same raw/aggregate view the old standalone Cookies/Query
 * Params tabs had. */
function FilteredIdentifiersView({
  uploadId,
  source,
  onTraceKey,
}: {
  uploadId: string
  source: RecordsSource
  onTraceKey?: (key: string) => void
}) {
  const [showAll, setShowAll] = useState(false)

  const [nameQuery, setNameQuery] = useState('')
  const debouncedNameQuery = useDebouncedValue(nameQuery)
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]>('Appearances')
  const [excludeCommon, setExcludeCommon] = useState(true)
  const [minAppearances, setMinAppearances] = useState(20)
  const debouncedMinAppearances = useDebouncedValue(minAppearances)
  const [maxUniqueValues, setMaxUniqueValues] = useState(5)
  const debouncedMaxUniqueValues = useDebouncedValue(maxUniqueValues)
  const [minAvgLength, setMinAvgLength] = useState(20)
  const debouncedMinAvgLength = useDebouncedValue(minAvgLength)
  const [minAvgEntropy, setMinAvgEntropy] = useState(2.5)
  const debouncedMinAvgEntropy = useDebouncedValue(minAvgEntropy)

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      'identifiers',
      uploadId,
      debouncedNameQuery,
      sortBy,
      excludeCommon,
      debouncedMinAppearances,
      debouncedMaxUniqueValues,
      debouncedMinAvgLength,
      debouncedMinAvgEntropy,
    ],
    queryFn: () =>
      fetchIdentifiers(uploadId, {
        min_appearances: debouncedMinAppearances,
        max_unique_values: debouncedMaxUniqueValues,
        min_avg_length: debouncedMinAvgLength,
        min_avg_entropy: debouncedMinAvgEntropy,
        name_query: debouncedNameQuery,
        exclude_common: excludeCommon,
        sort_by: sortBy,
      }),
    placeholderData: (previous) => previous,
    enabled: !showAll,
  })

  return (
    <>
      <FormRow>
        <label className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Show all (ignore identifier filter)
        </label>
      </FormRow>

      <div className={showAll ? 'pointer-events-none opacity-50' : undefined}>
        <h3 className="text-base font-semibold">Stable Identifier Detection</h3>
        <HelpText>
          Flags {source === 'cookies' ? 'cookies' : source === 'query-params' ? 'query params' : 'JSON body fields'}{' '}
          that appear often, take on few distinct values, and look sufficiently random/long to be a session,
          tracking, or auth token -- rather than an ordinary low-cardinality param like <code>sort</code> or{' '}
          <code>lang</code>.
          {source === 'body-fields' && (
            <> Catches an identifier a site only ever hands back inside a JSON payload -- a UID2 token, an email hash, a resolved third-party ID -- that never shows up as a cookie or query param at all.</>
          )}
        </HelpText>

        <Disclosure summary="Common noise keys">
          <p className="text-[13px] text-text-muted">
            page, limit, offset, sort, order, q, query, lang, locale, cache, v, version, format, type, action,
            utm_source, utm_medium, utm_campaign, utm_term, utm_content
          </p>
        </Disclosure>

        <FormRow>
          <NameAndSortFields
            nameQuery={nameQuery}
            onNameQueryChange={setNameQuery}
            namePlaceholder="e.g. sess, token, sid"
            sortBy={sortBy}
            onSortByChange={setSortBy}
            disabled={showAll}
          />
          <label className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
            <input
              type="checkbox"
              checked={excludeCommon}
              onChange={(e) => setExcludeCommon(e.target.checked)}
              disabled={showAll}
            />
            Exclude common noise keys
          </label>
        </FormRow>

        <FormRow>
          <RangeField
            label="Minimum appearances"
            value={minAppearances}
            min={1}
            max={200}
            onChange={setMinAppearances}
            disabled={showAll}
          />
          <RangeField
            label="Max unique values"
            value={maxUniqueValues}
            min={1}
            max={20}
            onChange={setMaxUniqueValues}
            disabled={showAll}
          />
        </FormRow>

        <FormRow>
          <RangeField
            label="Minimum avg value length"
            value={minAvgLength}
            min={0}
            max={64}
            onChange={setMinAvgLength}
            disabled={showAll}
          />
          <RangeField
            label="Minimum avg entropy"
            value={minAvgEntropy}
            min={0}
            max={6}
            step={0.1}
            onChange={setMinAvgEntropy}
            formatValue={(v) => `${v.toFixed(1)} bits/char`}
            disabled={showAll}
          />
        </FormRow>
      </div>

      {showAll && <AllRecordsView uploadId={uploadId} source={source} />}

      {!showAll && isLoading && <LoadingState />}
      {!showAll && isError && <ErrorState label="Failed to load identifiers." />}

      {!showAll && data && (
        <>
          {source === 'cookies' && (
            <HelpText>
              First Seen As marks where a cookie turned up first: a Response Cookie was issued during this capture,
              a Request Cookie already existed.
            </HelpText>
          )}
          {source === 'body-fields' && (
            <HelpText>
              First Seen As marks which side of the exchange a field turned up on: POST Data (the request body) or
              Response Body. Dissemination tracing isn't available for body fields yet -- only cookies and query
              params can be traced there today.
            </HelpText>
          )}
          <IdentifiersSection
            label={SOURCE_LABELS[source]}
            identifiers={data[SOURCE_DATA_KEY[source]]}
            onTraceKey={source === 'body-fields' ? undefined : onTraceKey}
          />
        </>
      )}
    </>
  )
}

/** min_appearances/max_unique_values/min_avg_length/min_avg_entropy/
 * exclude_common don't affect the Known IDs section at all -- filter_known_ids
 * on the backend ignores them entirely. These are inert placeholders to
 * satisfy fetchIdentifiers' shared param shape, not a copy of the other
 * view's real defaults, so they're never meant to be kept in sync with it. */
const KNOWN_IDS_IGNORED_FILTER_PARAMS = {
  min_appearances: 1,
  max_unique_values: 20,
  min_avg_length: 0,
  min_avg_entropy: 0,
  exclude_common: false,
} as const

/** Known IDs: an exact-name match against studied vendors' documented
 * identifiers (see app.features.identifiers.filter_known_ids on the
 * backend). No entropy/cardinality filter sliders and no raw "Show all"
 * mode -- it's already the precise view by construction. */
function KnownIdsView({ uploadId, onTraceKey }: { uploadId: string; onTraceKey?: (key: string) => void }) {
  const [nameQuery, setNameQuery] = useState('')
  const debouncedNameQuery = useDebouncedValue(nameQuery)
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]>('Appearances')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['identifiers', uploadId, 'known-ids', debouncedNameQuery, sortBy],
    queryFn: () =>
      fetchIdentifiers(uploadId, {
        ...KNOWN_IDS_IGNORED_FILTER_PARAMS,
        name_query: debouncedNameQuery,
        sort_by: sortBy,
      }),
    placeholderData: (previous) => previous,
  })

  return (
    <>
      <h3 className="text-base font-semibold">Known Identifiers</h3>
      <HelpText>
        Matches cookie/query-param/body-field names against identifiers documented by studied ad-tech and identity
        vendors (UID2, ID5, RampID, Prebid...). This is an exact name match, not a heuristic, so a confirmed match is
        shown regardless of how rarely it appears -- the 4-signal thresholds used elsewhere in this tab don't apply
        here.
      </HelpText>

      <FormRow>
        <NameAndSortFields
          nameQuery={nameQuery}
          onNameQueryChange={setNameQuery}
          namePlaceholder="e.g. uid2, id5id"
          sortBy={sortBy}
          onSortByChange={setSortBy}
        />
      </FormRow>

      {isLoading && <LoadingState />}
      {isError && <ErrorState label="Failed to load identifiers." />}

      {data && (
        <>
          <HelpText>
            First Seen As marks which side of the exchange a field turned up on: Request/Response Cookie, POST Data,
            Response Body, or blank for a query param. Trace jumps to Dissemination, which only tracks cookie and
            query-param sightings -- a Known ID seen only inside a JSON body field won't be traceable there.
          </HelpText>
          <IdentifiersSection label="Known IDs" identifiers={data.known_ids} onTraceKey={onTraceKey} />
        </>
      )}
    </>
  )
}

export function IdentifiersView({ uploadId, onTraceKey }: IdentifiersViewProps) {
  const [source, setSource] = useState<Source>('known-ids')
  const isKnownIds = source === 'known-ids'

  return (
    <div>
      <FormRow>
        <SegmentedControl legend="Source" options={SOURCE_OPTIONS} value={source} onChange={(v) => setSource(v as Source)} />
      </FormRow>

      {/* Both views stay mounted the whole time (rather than swapping which
       * component type renders at this slot) so switching the Source control
       * back and forth never remounts-and-resets FilteredIdentifiersView's
       * filter state or KnownIdsView's search/sort state. */}
      <div className={isKnownIds ? undefined : 'hidden'}>
        <KnownIdsView uploadId={uploadId} onTraceKey={onTraceKey} />
      </div>
      <div className={isKnownIds ? 'hidden' : undefined}>
        <FilteredIdentifiersView
          uploadId={uploadId}
          source={source === 'known-ids' ? 'cookies' : source}
          onTraceKey={onTraceKey}
        />
      </div>
    </div>
  )
}
