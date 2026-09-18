import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDisseminationKeys, fetchDisseminationTimeline } from '../../api/dissemination'
import { fetchEncodingOptions } from '../../api/har'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { DisseminationSearchForm } from './DisseminationSearchForm'
import { DisseminationResults } from './DisseminationResults'

interface DisseminationViewProps {
  uploadId: string
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
  { header: 'URL', accessor: (r) => r.URL },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Value changed', accessor: (r) => (r['Value changed'] ? 'Yes' : '') },
]

interface SubmittedSearch {
  key: string
  encodings: string[]
}

/** Direct port of tabs/dissemination/dissemination_ui.py: key picker, an
 * always-live value timeline, then an explicit-submit dissemination scan. */
export function DisseminationView({ uploadId }: DisseminationViewProps) {
  const { data: keys } = useQuery({
    queryKey: ['dissemination-keys', uploadId],
    queryFn: () => fetchDisseminationKeys(uploadId),
  })
  const { data: encodingOptions } = useQuery({ queryKey: ['meta-encodings'], queryFn: fetchEncodingOptions })

  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [submittedSearch, setSubmittedSearch] = useState<SubmittedSearch | null>(null)

  useEffect(() => {
    if (keys && keys.length > 0 && selectedKey === null) setSelectedKey(keys[0])
  }, [keys, selectedKey])

  // A search's results only make sense for the key that produced them --
  // switching keys invalidates whatever was found before, same as the
  // original's (key, encodings) signature check.
  useEffect(() => {
    setSubmittedSearch(null)
  }, [selectedKey])

  const timelineQuery = useQuery({
    queryKey: ['dissemination-timeline', uploadId, selectedKey],
    queryFn: () => fetchDisseminationTimeline(uploadId, selectedKey as string),
    enabled: selectedKey !== null,
  })

  if (keys && keys.length === 0) {
    return <p>No query parameters or cookies found to trace.</p>
  }

  return (
    <div className="dissemination">
      <h3>Identifier Dissemination History</h3>
      <p className="overview__caption">
        Pick a query-param or cookie key to see how its value evolved over time, then search the whole HAR for every
        place that value shows up -- headers, URLs, bodies, other cookies -- beyond its original key.
      </p>

      {keys && (
        <div className="dissemination__key-picker">
          <label>
            Key to trace
            <select value={selectedKey ?? ''} onChange={(e) => setSelectedKey(e.target.value)}>
              {keys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {timelineQuery.data && (
        <>
          <div className="metrics-row">
            <div className="metric">
              <span className="metric__label">Sightings</span>
              <span className="metric__value">{timelineQuery.data.sightings}</span>
            </div>
            <div className="metric">
              <span className="metric__label">Distinct Values</span>
              <span className="metric__value">{timelineQuery.data.distinct_values}</span>
            </div>
            <div className="metric">
              <span className="metric__label">Source</span>
              <span className="metric__value">{timelineQuery.data.origins.join(' & ')}</span>
            </div>
          </div>

          <p className="dissemination__banner">
            First seen as a <strong>{timelineQuery.data.first_seen.origin}</strong> at{' '}
            {timelineQuery.data.first_seen.when} ({timelineQuery.data.first_seen.method}{' '}
            {timelineQuery.data.first_seen.domain}) with value <code>{timelineQuery.data.first_seen.value}</code>.
          </p>

          <h4>Value Timeline</h4>
          <p className="overview__caption">
            One row per sighting, ordered by HAR timestamp. 'Value changed' flags a sighting whose value differs
            from the one immediately before it.
          </p>
          <DataTable
            columns={TIMELINE_COLUMNS}
            rows={timelineQuery.data.timeline as unknown as TimelineRow[]}
            rowKey={(_, i) => i}
          />

          <h4>Dissemination</h4>
          {encodingOptions && selectedKey && (
            <DisseminationSearchForm
              encodingOptions={encodingOptions}
              isSearching={false}
              onSearch={(encodings) => setSubmittedSearch({ key: selectedKey, encodings })}
            />
          )}

          {submittedSearch ? (
            <DisseminationResults uploadId={uploadId} submittedSearch={submittedSearch} />
          ) : (
            <p className="overview__caption">No search run yet for this key and encoding selection.</p>
          )}
        </>
      )}
    </div>
  )
}
