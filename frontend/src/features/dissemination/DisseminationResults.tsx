import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchDissemination } from '../../api/dissemination'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import type { DisseminationFirstSeen, InitiatorChainLink } from '../../api/types'
import { EntryListWithDetail } from '../../components/EntryListWithDetail'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { ErrorState, LoadingState } from '../../components/QueryState'
import { Tabs, type TabDefinition } from '../../components/Tabs'
import { DisseminationGraph } from './DisseminationGraph'
import type { DomainRow } from './disseminationGraphData'

interface DisseminationResultsProps {
  uploadId: string
  submittedSearch: { key: string; encodings: string[] }
  /** Chain of requests that (transitively) caused the traced key's first
   * sighting -- already computed once by the always-live timeline fetch in
   * DisseminationView, so it's passed down rather than re-fetched here. */
  initiatorChain: InitiatorChainLink[]
  /** Where/when the traced key was first seen -- same timeline fetch as
   * initiatorChain, needed as the graph's root/origin node. */
  firstSeen: DisseminationFirstSeen
}

const DOMAIN_COLUMNS: DataTableColumn<DomainRow>[] = [
  { header: 'Domain', accessor: (r) => r.Domain },
  { header: 'Entries Hit', accessor: (r) => r['Entries Hit'] },
  { header: 'Cookie origin', accessor: (r) => r['Cookie origin'] },
  { header: 'Fields', accessor: (r) => r.Fields },
  { header: 'Distinct Values Seen', accessor: (r) => r['Distinct Values Seen'] },
]

/** Results for an already-submitted search: a switchable By Domain /
 * Initiator Traced Entries view, then the live narrow/highlight filters
 * over the matching-entries list. Re-queries the backend on a narrow/
 * highlight change (debounced) but only ever with the key/encodings from
 * the last explicit submit, never a mid-edit draft. */
export function DisseminationResults({ uploadId, submittedSearch, initiatorChain, firstSeen }: DisseminationResultsProps) {
  const [narrowQuery, setNarrowQuery] = useState('')
  const debouncedNarrow = useDebouncedValue(narrowQuery)
  const [highlightQuery, setHighlightQuery] = useState('')
  const debouncedHighlight = useDebouncedValue(highlightQuery)
  const [topView, setTopView] = useState('by-domain')
  // Independent: the switcher's Initiator Traced Entries list and the
  // always-visible Matching HAR Entries list each get their own detail
  // panel, sized to their own content, rather than sharing one.
  const [initiatorSelectedIndex, setInitiatorSelectedIndex] = useState<number | null>(null)
  const [matchesSelectedIndex, setMatchesSelectedIndex] = useState<number | null>(null)

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

  const selectedMatch = data.matches.find((m) => m.entry.index === matchesSelectedIndex)

  // A hop the chain couldn't resolve (its initiating URL wasn't captured in
  // this HAR) always ends up first once build_initiator_chain's result is
  // put in chronological order -- it's as far back as the trail goes.
  const danglingStart = initiatorChain[0]?.found === false ? initiatorChain[0] : null
  const tracedEntries = initiatorChain.flatMap((link) => (link.found && link.entry ? [link.entry] : []))

  const topViewTabs: TabDefinition[] = [
    {
      key: 'by-domain',
      label: 'By Domain',
      render: () => (
        <>
          <p className="my-1 mb-3 text-[13px] text-text-muted">
            Aggregated view: which hosts received/echoed this value, in how many entries, through which fields.
            Cookie origin is the earliest cookie hit on that host.
          </p>
          <DataTable columns={DOMAIN_COLUMNS} rows={data.by_domain as unknown as DomainRow[]} rowKey={(r) => r.Domain} />
        </>
      ),
    },
    {
      key: 'initiator-trace',
      label: 'Initiator Traced Entries',
      render: () => (
        <>
          <p className="my-1 mb-3 text-[13px] text-text-muted">
            The chain of requests that led up to this value's first sighting, following each entry's initiator back
            one hop at a time -- e.g. the page loaded a script, which loaded another, which made the request that
            first carried this value.
          </p>
          {tracedEntries.length === 0 && !danglingStart ? (
            <p className="my-1 mb-3 text-[13px] text-text-muted">
              No initiator recorded for the first sighting -- it was likely a top-level page load, not something
              triggered by another script.
            </p>
          ) : (
            <>
              {danglingStart && (
                <p className="my-1 mb-3 text-[13px] text-text-muted">
                  ⋯ trail starts here -- <code className="font-mono text-xs">{danglingStart.url}</code> (
                  {danglingStart.initiator_type}) wasn't captured in this HAR, so the chain can't go back further.
                </p>
              )}
              {tracedEntries.length > 0 && (
                <EntryListWithDetail
                  uploadId={uploadId}
                  items={tracedEntries}
                  selectedIndex={initiatorSelectedIndex}
                  onSelectRow={setInitiatorSelectedIndex}
                  onClose={() => setInitiatorSelectedIndex(null)}
                  emptyMessage="No initiator-traced entries."
                />
              )}
            </>
          )}
        </>
      ),
    },
    {
      key: 'graph',
      label: 'Dissemination Graph',
      render: () => (
        <>
          <p className="my-1 mb-3 text-[13px] text-text-muted">
            The whole story in one view: how this value's first sighting was caused, then where it spread
            afterward. Click a domain to narrow the Matching HAR Entries list below to it.
          </p>
          <DisseminationGraph
            firstSeen={firstSeen}
            initiatorChain={initiatorChain}
            byDomain={data.by_domain as unknown as DomainRow[]}
            onSelectDomain={(domain) => setNarrowQuery(`domain:${domain}`)}
          />
        </>
      ),
    },
  ]

  return (
    <div>
      <Tabs tabs={topViewTabs} variant="panel" activeTab={topView} onActiveTabChange={setTopView} />

      <h5 className="mt-3 text-sm font-semibold">Matching HAR Entries</h5>
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
      <EntryListWithDetail
        uploadId={uploadId}
        items={data.matches.map((m) => m.entry)}
        selectedIndex={matchesSelectedIndex}
        onSelectRow={setMatchesSelectedIndex}
        onClose={() => setMatchesSelectedIndex(null)}
        showMatchedFields
        emptyMessage="No matches for this filter."
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
    </div>
  )
}
