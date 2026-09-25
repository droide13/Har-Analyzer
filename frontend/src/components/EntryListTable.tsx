import type { EntrySummary } from '../api/types'
import { Badge } from './Badge'
import { DataTable, type DataTableColumn } from './DataTable'
import { statusTone } from '../lib/statusColor'

const BASE_COLUMNS: DataTableColumn<EntrySummary>[] = [
  {
    header: 'Status',
    accessor: (e) => <Badge tone={statusTone(e.status)}>{e.status || '—'}</Badge>,
    sizingText: (e) => e.status || '—',
  },
  { header: 'Method', accessor: (e) => e.method },
  { header: 'URL', accessor: (e) => e.url, className: 'font-mono text-xs' },
  { header: 'Domain', accessor: (e) => e.domain },
  { header: 'MIME', accessor: (e) => e.mime },
  { header: 'Time', accessor: (e) => `${e.time_ms.toFixed(1)} ms` },
  {
    header: 'Cookies',
    accessor: (e) => (e.req_cookie_count || e.res_cookie_count ? `${e.req_cookie_count}↑ ${e.res_cookie_count}↓` : null),
    sizingText: (e) => (e.req_cookie_count || e.res_cookie_count ? `${e.req_cookie_count}↑ ${e.res_cookie_count}↓` : ''),
  },
]

const MATCHED_FIELDS_COLUMN: DataTableColumn<EntrySummary> = {
  header: 'Matched Fields',
  accessor: (e) => (
    <div className="flex flex-nowrap items-center">
      {e.badges.map((badge, i) => (
        <Badge key={i} tone={badge.tone}>
          {badge.label}
        </Badge>
      ))}
    </div>
  ),
  // Sized to whichever row's badges are longest rather than capped/shrunk
  // to fit -- a row with many matched fields would otherwise have its
  // badges cut off with no way to see the rest. The table scrolls
  // horizontally instead.
  sizeToContent: true,
  // Badge text spells out the matched encoding/hash form too (e.g.
  // "Filtered via: Response Body (Base64, MD5)"), so this column needs the
  // real concatenated label text to size against -- the accessor's JSX
  // would otherwise size it against "[object Object]". Each badge pill also
  // has its own padding/margin the char-count heuristic can't see, so pad a
  // few extra chars per badge -- erring wide is fine here, erring narrow
  // reintroduces the clipping this column exists to avoid.
  sizingText: (e) => e.badges.map((b) => `${b.label}   `).join(''),
}

interface EntryListTableProps {
  items: EntrySummary[]
  selectedIndex: number | null
  onSelectRow: (index: number) => void
  /** Adds the Matched Fields column (badges) -- Network Log only has this
   * while a filter/highlight query is active; Dissemination always does,
   * since every row there only exists because it matched something. */
  showMatchedFields?: boolean
  emptyMessage?: string
}

/**
 * Entry list shared by Network Log and Dissemination's match results -- one
 * table implementation instead of two so their columns, row states, and
 * match-reason display can't drift apart again. Built on the shared
 * DataTable (native <table> + colgroup, TanStack column sizing/resize,
 * react-virtual row virtualization) rather than a bespoke layout, so it
 * inherits the same robust header/body alignment under horizontal scroll
 * and automatic re-fit when the entry detail panel opens beside it.
 */
export function EntryListTable({
  items,
  selectedIndex,
  onSelectRow,
  showMatchedFields = false,
  emptyMessage = 'No entries match the current filter.',
}: EntryListTableProps) {
  const columns = showMatchedFields ? [...BASE_COLUMNS, MATCHED_FIELDS_COLUMN] : BASE_COLUMNS

  return (
    <DataTable
      columns={columns}
      rows={items}
      rowKey={(e) => e.index}
      onRowClick={(e) => onSelectRow(e.index)}
      rowClassName={(e) => {
        // A ground truth match is a more alarming kind of "found it" than a
        // plain search-query highlight -- gets its own wash color instead
        // of collapsing into the same bg-highlight yellow every other
        // highlighted row uses, so the two don't read as the same thing.
        const hasGroundTruthMatch = e.badges.some((b) => b.tone === 'error')
        const rowTint = hasGroundTruthMatch ? 'bg-error-wash' : e.highlighted ? 'bg-highlight' : ''
        return [rowTint, e.index === selectedIndex ? 'outline outline-2 -outline-offset-2 outline-accent' : '']
          .filter(Boolean)
          .join(' ')
      }}
      emptyLabel={emptyMessage}
    />
  )
}
