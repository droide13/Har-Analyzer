import { useRef, type ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { EntrySummary } from '../../api/types'
import { Badge } from '../../components/Badge'
import { statusTone } from '../../lib/statusColor'
import { rowStateClassName } from '../../lib/rowState'

const ROW_HEIGHT_PX = 32

interface Column {
  header: string
  widthPx: number
  grow?: boolean
  render: (entry: EntrySummary) => ReactNode
  /** Plain-text value for a hover tooltip, so a value truncated by column
   * width is still readable without having to open the row's detail panel
   * (which the row's own onClick already does, so cells don't duplicate
   * that as a click action). */
  title: (entry: EntrySummary) => string
}

/**
 * Plain column config instead of a table library's column-def API: the
 * table needs no sorting/grouping (the backend already does the filtering),
 * so a full headless-table dependency would be more surface area than the
 * job needs. Pairs with react-virtual below for row virtualization.
 */
const COLUMNS: Column[] = [
  {
    header: 'Status',
    widthPx: 70,
    render: (e) => <Badge tone={statusTone(e.status)}>{e.status || '—'}</Badge>,
    title: (e) => e.status || 'Unknown',
  },
  { header: 'Method', widthPx: 70, render: (e) => e.method, title: (e) => e.method },
  {
    header: 'URL',
    widthPx: 480,
    grow: true,
    render: (e) => <span className="font-mono text-xs">{e.url}</span>,
    title: (e) => e.url,
  },
  { header: 'Domain', widthPx: 180, render: (e) => e.domain, title: (e) => e.domain },
  { header: 'MIME', widthPx: 140, render: (e) => e.mime, title: (e) => e.mime },
  { header: 'Time', widthPx: 80, render: (e) => `${e.time_ms.toFixed(1)} ms`, title: (e) => `${e.time_ms.toFixed(1)} ms` },
  {
    header: 'Cookies',
    widthPx: 90,
    render: (e) => (e.req_cookie_count || e.res_cookie_count ? `${e.req_cookie_count}↑ ${e.res_cookie_count}↓` : null),
    title: (e) => `${e.req_cookie_count} sent, ${e.res_cookie_count} received`,
  },
]

function cellStyle(col: Column): React.CSSProperties {
  return col.grow ? { flex: `1 1 ${col.widthPx}px`, minWidth: col.widthPx } : { flex: `0 0 ${col.widthPx}px` }
}

interface EntryTableProps {
  items: EntrySummary[]
  selectedIndex: number | null
  onSelectRow: (index: number) => void
}

/**
 * Virtualized replacement for the original's one-st.expander-per-row
 * pattern: only the rows actually scrolled into view are ever mounted,
 * regardless of how many entries are in the filtered result.
 *
 * Built from plain divs, not a real <table> -- a <tr> can't be
 * absolutely positioned (react-virtual's whole trick) while still
 * participating in normal table column-width layout, so a real table
 * here would render with columns that don't line up between rows. Flex
 * rows with matching fixed-width cells sidestep that entirely.
 */
export function EntryTable({ items, selectedIndex, onSelectRow }: EntryTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT_PX,
    overscan: 12,
  })

  return (
    <div className="h-[60vh] flex-1 min-w-0 overflow-auto rounded-md border border-border-strong shadow-sm" ref={scrollRef}>
      <div className="min-w-max" role="table">
        <div className="sticky top-0 z-10 flex border-b border-border bg-bg-subtle" role="row">
          {COLUMNS.map((col) => (
            <div
              key={col.header}
              className="px-2 py-1 text-[13px] font-medium text-text-muted"
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
                {COLUMNS.map((col) => (
                  <div
                    key={col.header}
                    title={col.title(entry)}
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
      {items.length === 0 && <p className="p-6 text-center text-text-muted">No entries match the current filter.</p>}
    </div>
  )
}
