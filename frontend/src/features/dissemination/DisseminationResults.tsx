import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchDissemination } from '../../api/dissemination'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { EntryDetailPanel } from '../../components/EntryDetailPanel'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { DisseminationMatchList } from './DisseminationMatchList'

interface DisseminationResultsProps {
  uploadId: string
  submittedSearch: { key: string; encodings: string[] }
}

interface DomainRow {
  Domain: string
  'Entries Hit': number
  'Cookie origin': string
  Fields: string
  'Distinct Values Seen': number
}

const DOMAIN_COLUMNS: DataTableColumn<DomainRow>[] = [
  { header: 'Domain', accessor: (r) => r.Domain },
  { header: 'Entries Hit', accessor: (r) => r['Entries Hit'] },
  { header: 'Cookie origin', accessor: (r) => r['Cookie origin'] },
  { header: 'Fields', accessor: (r) => r.Fields },
  { header: 'Distinct Values Seen', accessor: (r) => r['Distinct Values Seen'] },
]

/** Results for an already-submitted search: by-domain aggregate + the live
 * narrow/highlight filters over the matching-entries list. Re-queries the
 * backend on a narrow/highlight change (debounced) but only ever with the
 * key/encodings from the last explicit submit, never a mid-edit draft. */
export function DisseminationResults({ uploadId, submittedSearch }: DisseminationResultsProps) {
  const [narrowQuery, setNarrowQuery] = useState('')
  const debouncedNarrow = useDebouncedValue(narrowQuery)
  const [highlightQuery, setHighlightQuery] = useState('')
  const debouncedHighlight = useDebouncedValue(highlightQuery)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['dissemination-search', uploadId, submittedSearch, debouncedNarrow, debouncedHighlight],
    queryFn: () =>
      searchDissemination(uploadId, {
        key: submittedSearch.key,
        encodings: submittedSearch.encodings,
        narrow: debouncedNarrow,
        highlight: debouncedHighlight,
      }),
    placeholderData: (previous) => previous,
  })

  if (isLoading) return <p>Loading...</p>
  if (isError || !data) return <p className="overview__error">Failed to load dissemination results.</p>

  if (data.matches.length === 0 && data.by_domain.length === 0) {
    return <p>No further dissemination found beyond the key's own occurrences.</p>
  }

  const selectedMatch = data.matches.find((m) => m.entry.index === selectedIndex)

  return (
    <div>
      <h5>By Domain</h5>
      <p className="overview__caption">
        Aggregated view: which hosts received/echoed this value, in how many entries, through which fields. Cookie
        origin is the earliest cookie hit on that host.
      </p>
      <DataTable columns={DOMAIN_COLUMNS} rows={data.by_domain as unknown as DomainRow[]} rowKey={(r) => r.Domain} />

      <h5>Matching Entries</h5>
      <p className="overview__caption">Ordered by HAR timestamp, oldest first.</p>
      <div className="search-controls__row">
        <label>
          Narrow these matches (discards)
          <input
            type="text"
            value={narrowQuery}
            onChange={(e) => setNarrowQuery(e.target.value)}
            placeholder="e.g. domain:example.com, status:200"
          />
        </label>
        <label>
          Highlight within matches (keeps all)
          <input
            type="text"
            value={highlightQuery}
            onChange={(e) => setHighlightQuery(e.target.value)}
            placeholder="e.g. cookie, status:200"
          />
        </label>
      </div>

      <div className="network-log__body">
        <DisseminationMatchList matches={data.matches} selectedIndex={selectedIndex} onSelectRow={setSelectedIndex} />
        {selectedIndex !== null && (
          <EntryDetailPanel
            uploadId={uploadId}
            index={selectedIndex}
            onClose={() => setSelectedIndex(null)}
            extraTabs={
              selectedMatch
                ? [
                    {
                      key: 'matches',
                      label: 'Matches',
                      render: () => (
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Field</th>
                              <th>Value</th>
                              <th>Forms</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedMatch.reasons.map((r, i) => (
                              <tr key={i}>
                                <td>{r.Field}</td>
                                <td>{r.Value}</td>
                                <td>{r.Forms}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ),
                    },
                  ]
                : []
            }
          />
        )}
      </div>
    </div>
  )
}
