import { useRef, type ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { EntrySummary } from '../api/types'
import { Badge } from './Badge'
import { statusTone } from '../lib/statusColor'

const ROW_HEIGHT_PX = 32

/** Highlight (the row matched the highlight query) and selection (its detail
 * panel is open) are independent, so a row can carry both at once. */
function rowStateClassName(highlighted: boolean, selected: boolean): string {
  return [
    'cursor-pointer border-b border-border hover:bg-bg-subtle',
    highlighted ? 'bg-highlight' : '',
    selected ? 'outline outline-2 -outline-offset-2 outline-accent' : '',
  ]
    .filter(Boolean)
    .join(' ')
}

interface Column {
  header: string
  widthPx: number
  grow?: boolean
  render: (entry: EntrySummary) => ReactNode
}

const BASE_COLUMNS: Column[] = [
  {
    header: 'Status',
    widthPx: 70,
    render: (e) => <Badge tone={statusTone(e.status)}>{e.status || '—'}</Badge>,
  },
  { header: 'Method', widthPx: 70, render: (e) => e.method },
  {
    header: 'URL',
    widthPx: 240,
    grow: true,
    render: (e) => <span className="font-mono text-xs">{e.url}</span>,
  },
  { header: 'Domain', widthPx: 180, render: (e) => e.domain },
  { header: 'MIME', widthPx: 140, render: (e) => e.mime },
  { header: 'Time', widthPx: 80, render: (e) => `${e.time_ms.toFixed(1)} ms` },
  {
    header: 'Cookies',
    widthPx: 90,
    render: (e) => (e.req_cookie_count || e.res_cookie_count ? `${e.req_cookie_count}↑ ${e.res_cookie_count}↓` : null),
  },
]

const MATCHED_FIELDS_COLUMN: Column = {
  header: 'Matched Fields',
  // Badge text now spells out the matched encoding/hash form too (e.g.
  // "Filtered via: Response Body (Base64, MD5)"), well past what a fixed
  // 260px held -- grow like the URL column so it gets whatever room's left.
  widthPx: 340,
  grow: true,
  render: (e) => (
    <div className="flex flex-nowrap items-center overflow-hidden">
      {e.badges.map((badge, i) => (
        <Badge key={i} tone={badge.tone}>
          {badge.label}
        </Badge>
      ))}
    </div>
  ),
}

function cellStyle(col: Column): React.CSSProperties {
  return col.grow ? { flex: `1 1 ${col.widthPx}px`, minWidth: col.widthPx } : { flex: `0 0 ${col.widthPx}px` }
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
 * Virtualized entry list shared by Network Log and Dissemination's match
 * results -- one table implementation instead of two so their columns,
 * row states, and match-reason display can't drift apart again. Only the
 * rows actually scrolled into view are ever mounted, regardless of how many
 * entries are in the result.
 *
 * Built from plain divs, not a real <table> -- a <tr> can't be absolutely
 * positioned (react-virtual's whole trick) while still participating in
 * normal table column-width layout, so a real table here would render with
 * columns that don't line up between rows. Flex rows with matching
 * fixed-width cells sidestep that entirely.
 */
export function EntryListTable({
  items,
  selectedIndex,
  onSelectRow,
  showMatchedFields = false,
  emptyMessage = 'No entries match the current filter.',
}: EntryListTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const columns = showMatchedFields ? [...BASE_COLUMNS, MATCHED_FIELDS_COLUMN] : BASE_COLUMNS

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT_PX,
    overscan: 12,
  })

  return (
    <div className="max-h-[60vh] flex-1 min-w-0 overflow-auto rounded-md border border-border-strong shadow-sm" ref={scrollRef}>
      <div className="min-w-max" role="table">
        <div className="sticky top-0 z-10 flex border-b border-border bg-bg-subtle" role="row">
          {columns.map((col) => (
            <div
              key={col.header}
              className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 text-[13px] font-medium text-text-muted"
              role="columnheader"
              style={cellStyle(col)}
            >
              {col.header}
            </div>
          ))}
        </div>
        <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const entry = items[virtualRow.index]
            return (
              <div
                key={entry.index}
                role="row"
                onClick={() => onSelectRow(entry.index)}
                className={`flex items-center ${rowStateClassName(entry.highlighted, entry.index === selectedIndex)}`}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: ROW_HEIGHT_PX,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {columns.map((col) => (
                  <div
                    key={col.header}
                    className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 text-[13px]"
                    role="cell"
                    style={cellStyle(col)}
                  >
                    {col.render(entry)}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>
      {items.length === 0 && <p className="p-6 text-center text-text-muted">{emptyMessage}</p>}
    </div>
  )
}
