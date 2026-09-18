import type { DisseminationMatchRow } from '../../api/types'
import { statusColor } from '../../lib/statusColor'

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
    <div className="entry-table__scroll">
      <table className="entry-table entry-table--fixed">
        <thead>
          <tr>
            <th style={{ width: 70 }}>Status</th>
            <th style={{ width: 70 }}>Method</th>
            <th>URL</th>
            <th style={{ width: 260 }}>Matched Fields</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((row) => (
            <tr
              key={row.entry.index}
              onClick={() => onSelectRow(row.entry.index)}
              className={[
                'entry-table__row',
                row.entry.highlighted ? 'entry-table__row--highlighted' : '',
                row.entry.index === selectedIndex ? 'entry-table__row--selected' : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <td className={statusColor(row.entry.status)}>{row.entry.status || '—'}</td>
              <td>{row.entry.method}</td>
              <td className="entry-table__url">{row.entry.url}</td>
              <td className="entry-table__badges">
                {row.badges.map((badge) => (
                  <span key={badge} className="badge badge--orange">
                    {badge}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {matches.length === 0 && <p className="entry-table__empty">No matches for this filter.</p>}
    </div>
  )
}
