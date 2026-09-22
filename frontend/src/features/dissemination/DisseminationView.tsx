import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDisseminationKeys, fetchDisseminationTimeline } from '../../api/dissemination'
import { fetchEncodingOptions } from '../../api/har'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { Disclosure } from '../../components/Disclosure'
import { MetricsRow } from '../../components/MetricsRow'
import { Select } from '../../components/Select'
import { DisseminationSearchForm } from './DisseminationSearchForm'
import { DisseminationResults } from './DisseminationResults'

interface DisseminationViewProps {
  uploadId: string
  /** A key traced in from another tab (e.g. the Identifiers panel's "Trace"
   * button): selects that key and auto-runs its dissemination search.
   * Applied once, then cleared via onInitialTargetConsumed so navigating
   * back to this tab later doesn't re-apply it over a manual selection. */
  initialTarget?: { key: string } | null
  onInitialTargetConsumed?: () => void
}

interface TimelineRow {
  Started: string
  Origin: string
  Method: string
  Host: string
  URL: string
  Value: string
  'Value changed': boolean
}

const TIMELINE_COLUMNS: DataTableColumn<TimelineRow>[] = [
  { header: 'Started', accessor: (r) => r.Started },
  { header: 'Origin', accessor: (r) => r.Origin },
  { header: 'Method', accessor: (r) => r.Method },
  { header: 'Host', accessor: (r) => r.Host },
  { header: 'URL', accessor: (r) => r.URL, className: 'font-mono text-xs' },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Value changed', accessor: (r) => (r['Value changed'] ? 'Yes' : '') },
]

interface SubmittedSearch {
  key: string
  encodings: string[]
}

/** Direct port of tabs/dissemination/dissemination_ui.py: key picker, an
 * always-live value timeline, then an explicit-submit dissemination scan. */
export function DisseminationView({ uploadId, initialTarget, onInitialTargetConsumed }: DisseminationViewProps) {
  const { data: keys } = useQuery({
    queryKey: ['dissemination-keys', uploadId],
    queryFn: () => fetchDisseminationKeys(uploadId),
  })
  const { data: encodingOptions } = useQuery({ queryKey: ['meta-encodings'], queryFn: fetchEncodingOptions })

  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [submittedSearch, setSubmittedSearch] = useState<SubmittedSearch | null>(null)

  // A search's results only make sense for the key that produced them --
  // switching keys invalidates whatever was found before, same as the
  // original's (key, encodings) signature check. Only wired up to the
  // user-facing key picker (handleKeyChange), not to every selectedKey
  // change, so the auto-search below can set selectedKey + submittedSearch
  // together without this immediately wiping the latter out.
  function handleKeyChange(key: string) {
    setSelectedKey(key)
    setSubmittedSearch(null)
  }

  // Keep the latest callback without making it an effect dependency --
  // App.tsx passes a fresh closure every render, which would otherwise
  // re-run this effect on every unrelated re-render.
  const onInitialTargetConsumedRef = useRef(onInitialTargetConsumed)
  useEffect(() => {
    onInitialTargetConsumedRef.current = onInitialTargetConsumed
  })

  useEffect(() => {
    if (!initialTarget || !encodingOptions) return
    setSelectedKey(initialTarget.key)
    setSubmittedSearch({ key: initialTarget.key, encodings: encodingOptions })
    onInitialTargetConsumedRef.current?.()
  }, [initialTarget, encodingOptions])

  const timelineQuery = useQuery({
    queryKey: ['dissemination-timeline', uploadId, selectedKey],
    queryFn: () => fetchDisseminationTimeline(uploadId, selectedKey as string),
    enabled: selectedKey !== null,
  })

  if (keys && keys.length === 0) {
    return <p>No query parameters or cookies found to trace.</p>
  }

  return (
    <div>
      <h3 className="text-base font-semibold">Identifier Dissemination History</h3>
      <p className="my-1 mb-3 text-[13px] text-text-muted">
        Pick a query-param or cookie key to see how its value evolved over time, then search the whole HAR for every
        place that value shows up -- headers, URLs, bodies, other cookies -- beyond its original key.
      </p>

      {keys && (
        <label className="mb-2 flex max-w-xs flex-col gap-1 text-[13px] text-text-muted">
          Key to trace
          <Select
            value={selectedKey ?? ''}
            onChange={handleKeyChange}
            options={keys}
            ariaLabel="Key to trace"
            placeholder="Select a key..."
          />
        </label>
      )}

      {selectedKey === null && (
        <p className="my-1 mb-3 text-[13px] text-text-muted">Pick a key above to load its dissemination history.</p>
      )}

      {timelineQuery.data && (
        <>
          <MetricsRow
            metrics={[
              { label: 'Sightings', value: timelineQuery.data.sightings },
              { label: 'Distinct Values', value: timelineQuery.data.distinct_values },
              { label: 'Source', value: timelineQuery.data.origins.join(' & ') },
            ]}
          />

          <p className="my-2 rounded-md bg-bg-subtle px-3 py-2 text-[13px]">
            First seen as a <strong>{timelineQuery.data.first_seen.origin}</strong> at{' '}
            {timelineQuery.data.first_seen.when} ({timelineQuery.data.first_seen.method}{' '}
            {timelineQuery.data.first_seen.domain}) with value <code>{timelineQuery.data.first_seen.value}</code>.
          </p>

          <Disclosure summary={<span className="text-sm font-semibold text-text">Value Timeline</span>}>
            <p className="my-1 mb-3 text-[13px] text-text-muted">
              One row per sighting, ordered by HAR timestamp. 'Value changed' flags a sighting whose value differs
              from the one immediately before it.
            </p>
            <DataTable
              columns={TIMELINE_COLUMNS}
              rows={timelineQuery.data.timeline as unknown as TimelineRow[]}
              rowKey={(_, i) => i}
            />
          </Disclosure>

          <h4 className="text-sm font-semibold">Dissemination</h4>
          {encodingOptions && selectedKey && (
            <DisseminationSearchForm
              encodingOptions={encodingOptions}
              onSearch={(encodings) => setSubmittedSearch({ key: selectedKey, encodings })}
              hasSearched={submittedSearch !== null}
            />
          )}

          {submittedSearch ? (
            <DisseminationResults
              uploadId={uploadId}
              submittedSearch={submittedSearch}
              initiatorChain={timelineQuery.data.initiator_chain}
            />
          ) : (
            <p className="my-1 mb-3 text-[13px] text-text-muted">No search run yet for this key and encoding selection.</p>
          )}
        </>
      )}
    </div>
  )
}
