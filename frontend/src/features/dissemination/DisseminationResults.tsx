import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchDissemination } from '../../api/dissemination'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { EntryDetailPanel } from '../../components/EntryDetailPanel'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { ErrorState, LoadingState } from '../../components/QueryState'
import { DisseminationMatchList } from './DisseminationMatchList'

interface DisseminationResultsProps {
  uploadId: string
  submittedSearch: { key: string; encodings: string[] }
  /** Seeds the narrow filter on mount -- set when this search was
   * auto-triggered from a traced value, so results start narrowed to it. */
  initialNarrowQuery?: string
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
export function DisseminationResults({ uploadId, submittedSearch, initialNarrowQuery }: DisseminationResultsProps) {
  const [narrowQuery, setNarrowQuery] = useState(initialNarrowQuery ?? '')
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

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState label="Failed to load dissemination results." />

  if (data.matches.length === 0 && data.by_domain.length === 0) {
    return <p>No further dissemination found beyond the key's own occurrences.</p>
  }

  const selectedMatch = data.matches.find((m) => m.entry.index === selectedIndex)

  return (
    <div>
      <h5 className="text-sm font-semibold">By Domain</h5>
      <p className="my-1 mb-3 text-[13px] text-text-muted">
        Aggregated view: which hosts received/echoed this value, in how many entries, through which fields. Cookie
        origin is the earliest cookie hit on that host.
      </p>
      <DataTable columns={DOMAIN_COLUMNS} rows={data.by_domain as unknown as DomainRow[]} rowKey={(r) => r.Domain} />

      <h5 className="text-sm font-semibold">Matching Entries</h5>
      <p className="my-1 mb-3 text-[13px] text-text-muted">Ordered by HAR timestamp, oldest first.</p>
      <FormRow>
        <FormField label="Narrow these matches (discards)">
          <input
            type="text"
            className={fieldInputClasses}
            value={narrowQuery}
            onChange={(e) => setNarrowQuery(e.target.value)}
            placeholder="e.g. domain:example.com, status:200"
          />
        </FormField>
        <FormField label="Highlight within matches (keeps all)">
          <input
            type="text"
            className={fieldInputClasses}
            value={highlightQuery}
            onChange={(e) => setHighlightQuery(e.target.value)}
            placeholder="e.g. cookie, status:200"
          />
        </FormField>
      </FormRow>

      {/* The detail panel docks to the viewport edge (fixed, full height)
          rather than sitting inline, so this padding is what makes room for
          it instead of letting it cover the match list. */}
      <div className={selectedIndex !== null ? 'pr-[420px]' : ''}>
        <DisseminationMatchList matches={data.matches} selectedIndex={selectedIndex} onSelectRow={setSelectedIndex} />
      </div>
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
                      <DataTable
                        variant="compact"
                        columns={[
                          { header: 'Field', accessor: (r: (typeof selectedMatch.reasons)[number]) => r.Field },
                          { header: 'Value', accessor: (r: (typeof selectedMatch.reasons)[number]) => r.Value },
                          { header: 'Forms', accessor: (r: (typeof selectedMatch.reasons)[number]) => r.Forms },
                        ]}
                        rows={selectedMatch.reasons}
                        rowKey={(_, i) => i}
                      />
                    ),
                  },
                ]
              : []
          }
        />
      )}
    </div>
  )
}
