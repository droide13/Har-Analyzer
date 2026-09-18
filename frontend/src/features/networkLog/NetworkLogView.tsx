import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEncodingOptions, fetchEntries, fetchMethodOrder, fetchScopeOptions } from '../../api/har'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { SearchControls } from './SearchControls'
import { EntryTable } from './EntryTable'
import { EntryDetailPanel } from '../../components/EntryDetailPanel'
import { Pagination } from './Pagination'

interface NetworkLogViewProps {
  uploadId: string
}

const DEFAULT_SCOPE = 'any'
const DEFAULT_PAGE_SIZE = 50

/**
 * Orchestrates the Network Log tab: search/filter state, the meta option
 * lists (methods/encodings/scopes -- fetched once from the backend so
 * they're never hardcoded here), the paginated entry query, and the
 * optional detail panel for a selected row.
 */
export function NetworkLogView({ uploadId }: NetworkLogViewProps) {
  const { data: methodOrder } = useQuery({ queryKey: ['meta-methods'], queryFn: fetchMethodOrder })
  const { data: encodingOptions } = useQuery({ queryKey: ['meta-encodings'], queryFn: fetchEncodingOptions })
  const { data: scopeOptions } = useQuery({ queryKey: ['meta-scopes'], queryFn: fetchScopeOptions })

  // Raw values drive the input fields directly (instant typing feedback);
  // debounced values drive the actual query, so a fast typist doesn't fire
  // an HTTP request per keystroke.
  const [filterQuery, setFilterQuery] = useState('')
  const debouncedFilterQuery = useDebouncedValue(filterQuery)
  const [highlightQuery, setHighlightQuery] = useState('')
  const debouncedHighlightQuery = useDebouncedValue(highlightQuery)
  const [scope, setScope] = useState(DEFAULT_SCOPE)
  const [selectedMethods, setSelectedMethods] = useState<string[]>([])
  // null = "no user choice yet, default to every fetched encoding checked"
  // (matches the original's all-checked-by-default). Once the user toggles
  // one, this becomes a real Set that fully owns the checked state.
  const [customEncodings, setCustomEncodings] = useState<Set<string> | null>(null)
  const selectedEncodings = customEncodings ?? new Set(encodingOptions ?? [])
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [page, setPage] = useState(1)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  // A changed filter/highlight/scope/method/encoding invalidates the current
  // page, same as the original's session-state "signature" reset.
  const signature = JSON.stringify([
    debouncedFilterQuery,
    debouncedHighlightQuery,
    scope,
    selectedMethods,
    [...selectedEncodings].sort(),
  ])
  useEffect(() => {
    setPage(1)
  }, [signature])

  const entriesQuery = useQuery({
    queryKey: ['entries', uploadId, signature, page, pageSize],
    queryFn: () =>
      fetchEntries(uploadId, {
        q: debouncedFilterQuery,
        h: debouncedHighlightQuery,
        scope,
        methods: selectedMethods,
        encodings: [...selectedEncodings],
        page,
        page_size: pageSize,
      }),
    enabled: Boolean(encodingOptions), // wait for the "all checked" default to be resolvable
    placeholderData: (previous) => previous,
  })

  const data = entriesQuery.data

  return (
    <div className="network-log">
      {methodOrder && encodingOptions && scopeOptions && (
        <SearchControls
          filterQuery={filterQuery}
          onFilterQueryChange={setFilterQuery}
          highlightQuery={highlightQuery}
          onHighlightQueryChange={setHighlightQuery}
          scope={scope}
          onScopeChange={setScope}
          scopeOptions={scopeOptions}
          methodOrder={methodOrder}
          selectedMethods={selectedMethods}
          onMethodsChange={setSelectedMethods}
          encodingOptions={encodingOptions}
          selectedEncodings={selectedEncodings}
          onEncodingsChange={setCustomEncodings}
          pageSize={pageSize}
          onPageSizeChange={setPageSize}
        />
      )}

      {data && (
        <>
          <p className="network-log__summary">
            Showing <strong>{data.filtered}</strong> items
            {debouncedHighlightQuery.trim() && ` (${data.highlighted} highlighted)`} out of {data.total} total
            entries.
          </p>
          <Pagination page={data.page} totalPages={data.total_pages} onPageChange={setPage} />
          <div className="network-log__body">
            <EntryTable items={data.items} selectedIndex={selectedIndex} onSelectRow={setSelectedIndex} />
            {selectedIndex !== null && (
              <EntryDetailPanel uploadId={uploadId} index={selectedIndex} onClose={() => setSelectedIndex(null)} />
            )}
          </div>
        </>
      )}

      {entriesQuery.isError && <p className="network-log__error">Failed to load entries.</p>}
    </div>
  )
}
