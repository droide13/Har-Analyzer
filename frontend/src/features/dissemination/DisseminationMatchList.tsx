import type { DisseminationMatchRow } from '../../api/types'
import { Badge } from '../../components/Badge'
import { statusTone } from '../../lib/statusColor'
import { rowStateClassName } from '../../lib/rowState'

interface DisseminationMatchListProps {
  matches: DisseminationMatchRow[]
  selectedIndex: number | null
  onSelectRow: (index: number) => void
}

/** Plain (non-virtualized) list of dissemination matches -- one row per
 * entry with badges for which fields the value hit, mirroring the
 * original's per-row expander title. Row click opens the shared
 * EntryDetailPanel, same as Network Log. */
export function DisseminationMatchList({ matches, selectedIndex, onSelectRow }: DisseminationMatchListProps) {
  return (
    <div className="flex-1 min-w-0 h-[60vh] overflow-auto rounded-md border border-border-strong shadow-sm">
      <table className="w-full table-fixed border-collapse">
        <thead>
          <tr>
            <th className="w-[70px] sticky top-0 z-10 border-b border-border bg-bg-subtle px-2 py-1 text-left text-[13px] font-medium text-text-muted">
              Status
            </th>
            <th className="w-[70px] sticky top-0 z-10 border-b border-border bg-bg-subtle px-2 py-1 text-left text-[13px] font-medium text-text-muted">
              Method
            </th>
            <th className="sticky top-0 z-10 border-b border-border bg-bg-subtle px-2 py-1 text-left text-[13px] font-medium text-text-muted">
              URL
            </th>
            <th className="w-[260px] sticky top-0 z-10 border-b border-border bg-bg-subtle px-2 py-1 text-left text-[13px] font-medium text-text-muted">
              Matched Fields
            </th>
          </tr>
        </thead>
        <tbody>
          {matches.map((row) => (
            <tr
              key={row.entry.index}
              onClick={() => onSelectRow(row.entry.index)}
              className={rowStateClassName(row.entry.highlighted, row.entry.index === selectedIndex)}
            >
              <td title={row.entry.status || 'Unknown'} className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 text-[13px]">
                <Badge tone={statusTone(row.entry.status)}>{row.entry.status || '—'}</Badge>
              </td>
              <td title={row.entry.method} className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 text-[13px]">
                {row.entry.method}
              </td>
              <td title={row.entry.url} className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 font-mono text-xs">
                {row.entry.url}
              </td>
              <td className="px-2 py-1 text-[13px] whitespace-normal">
                {row.badges.map((badge) => (
                  <Badge key={badge} tone="orange">
                    {badge}
                  </Badge>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {matches.length === 0 && <p className="p-6 text-center text-text-muted">No matches for this filter.</p>}
    </div>
  )
}
