import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
import { IdentifiersSection } from './IdentifiersSection'

interface IdentifiersViewProps {
  uploadId: string
  /** Wires up each key's "Trace" button -- jumps to the Dissemination tab
   * with that key pre-selected. Only reachable in identifier-filter mode --
   * "Show all" mode has no single value to trace, same as the old Cookies/
   * Query Params tabs never had one. */
  onTraceKey?: (key: string) => void
}

type Source = 'cookies' | 'query-params'

const SOURCE_OPTIONS = [
  { value: 'cookies', label: 'Cookies' },
  { value: 'query-params', label: 'Query Parameters' },
]

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

/** "Show all" mode: the full raw/aggregate listing for one source, unfiltered
 * -- what the old standalone Cookies/Query Params tabs showed. */
function AllRecordsView({ uploadId, source }: { uploadId: string; source: Source }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['all-records', uploadId, source],
    queryFn: () => (source === 'cookies' ? fetchCookies(uploadId) : fetchQueryParams(uploadId)),
    placeholderData: (previous) => previous,
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState label="Failed to load records." />

  if (data.records.length === 0) {
    return <p>{source === 'cookies' ? 'No cookies found.' : 'No query string parameters found.'}</p>
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

/** Cookies, Query Params, and stable-identifier detection all live here now:
 * a source switch (Cookies / Query Params) plus a "Show all" kill switch
 * that either applies the 4-signal identifier filter (sliders stay pinned
 * above the table either way) or bypasses it entirely for the same raw/
 * aggregate view the old standalone Cookies/Query Params tabs had. */
export function IdentifiersView({ uploadId, onTraceKey }: IdentifiersViewProps) {
  const [source, setSource] = useState<Source>('cookies')
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
    <div>
      <FormRow>
        <SegmentedControl legend="Source" options={SOURCE_OPTIONS} value={source} onChange={(v) => setSource(v as Source)} />
        <label className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Show all (ignore identifier filter)
        </label>
      </FormRow>

      <div className={showAll ? 'pointer-events-none opacity-50' : undefined}>
        <h3 className="text-base font-semibold">Stable Identifier Detection</h3>
        <HelpText>
          Flags {source === 'cookies' ? 'cookies' : 'query params'} that appear often, take on few distinct values,
          and look sufficiently random/long to be a session, tracking, or auth token -- rather than an ordinary
          low-cardinality param like <code>sort</code> or <code>lang</code>.
        </HelpText>

        <Disclosure summary="Common noise keys">
          <p className="text-[13px] text-text-muted">
            page, limit, offset, sort, order, q, query, lang, locale, cache, v, version, format, type, action,
            utm_source, utm_medium, utm_campaign, utm_term, utm_content
          </p>
        </Disclosure>

        <FormRow>
          <FormField label="Search key name">
            <input
              type="text"
              className={fieldInputClasses}
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
              placeholder="e.g. sess, token, sid"
              disabled={showAll}
            />
          </FormField>
          <FormField label="Sort by">
            <select
              className={fieldInputClasses}
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as (typeof SORT_OPTIONS)[number])}
              disabled={showAll}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </FormField>
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
          <IdentifiersSection
            label={source === 'cookies' ? 'Cookies' : 'Query Parameters'}
            identifiers={source === 'cookies' ? data.cookies : data.query_params}
            onTraceKey={onTraceKey}
          />
        </>
      )}
    </div>
  )
}
