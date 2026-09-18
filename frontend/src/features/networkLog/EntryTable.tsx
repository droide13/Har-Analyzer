import { useRef, type ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { EntrySummary } from '../../api/types'

const ROW_HEIGHT_PX = 32

function statusColor(status: string): string {
  if (status.startsWith('2') || status.startsWith('3')) return 'status-ok'
  if (status) return 'status-error'
  return 'status-unknown'
}

interface Column {
  header: string
  widthPx: number
  grow?: boolean
  render: (entry: EntrySummary) => ReactNode
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
    render: (e) => <span className={statusColor(e.status)}>{e.status || '—'}</span>,
  },
  { header: 'Method', widthPx: 70, render: (e) => e.method },
  {
    header: 'URL',
    widthPx: 480,
    grow: true,
    render: (e) => <span className="virtual-table__url">{e.url}</span>,
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
    <div className="virtual-table__scroll" ref={scrollRef}>
      <div className="virtual-table" role="table">
        <div className="virtual-table__header" role="row">
          {COLUMNS.map((col) => (
            <div key={col.header} className="virtual-table__cell" role="columnheader" style={cellStyle(col)}>
              {col.header}
            </div>
          ))}
        </div>
        <div className="virtual-table__body" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const entry = items[virtualRow.index]
            return (
              <div
                key={entry.index}
                role="row"
                onClick={() => onSelectRow(entry.index)}
                className={[
                  'virtual-table__row',
                  entry.highlighted ? 'virtual-table__row--highlighted' : '',
                  entry.index === selectedIndex ? 'virtual-table__row--selected' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
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
                  <div key={col.header} className="virtual-table__cell" role="cell" style={cellStyle(col)}>
                    {col.render(entry)}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>
      {items.length === 0 && <p className="virtual-table__empty">No entries match the current filter.</p>}
    </div>
  )
}
