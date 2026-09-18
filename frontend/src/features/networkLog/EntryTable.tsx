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
  { header: 'URL', widthPx: 480, render: (e) => <span className="entry-table__url">{e.url}</span> },
  { header: 'Domain', widthPx: 180, render: (e) => e.domain },
  { header: 'MIME', widthPx: 140, render: (e) => e.mime },
  { header: 'Time', widthPx: 80, render: (e) => `${e.time_ms.toFixed(1)} ms` },
  {
    header: 'Cookies',
    widthPx: 90,
    render: (e) => (e.req_cookie_count || e.res_cookie_count ? `${e.req_cookie_count}↑ ${e.res_cookie_count}↓` : null),
  },
]

interface EntryTableProps {
  items: EntrySummary[]
  selectedIndex: number | null
  onSelectRow: (index: number) => void
}

/**
 * Virtualized replacement for the original's one-st.expander-per-row
 * pattern: only the rows actually scrolled into view are ever mounted,
 * regardless of how many entries are in the filtered result.
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
    <div className="entry-table__scroll" ref={scrollRef}>
      <table className="entry-table">
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th key={col.header} style={{ width: col.widthPx }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const entry = items[virtualRow.index]
            return (
              <tr
                key={entry.index}
                onClick={() => onSelectRow(entry.index)}
                className={[
                  'entry-table__row',
                  entry.highlighted ? 'entry-table__row--highlighted' : '',
                  entry.index === selectedIndex ? 'entry-table__row--selected' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: ROW_HEIGHT_PX,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {COLUMNS.map((col) => (
                  <td key={col.header} style={{ width: col.widthPx }}>
                    {col.render(entry)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
      {items.length === 0 && <p className="entry-table__empty">No entries match the current filter.</p>}
    </div>
  )
}
