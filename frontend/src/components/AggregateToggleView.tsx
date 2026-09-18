import { useState } from 'react'
import { DataTable, type DataTableColumn } from './DataTable'

interface AggregateToggleViewProps<TRaw, TAgg> {
  title: string
  metrics: { label: string; value: number }[]
  aggregatedCaption: string
  aggregatedColumns: DataTableColumn<TAgg>[]
  rawColumns: DataTableColumn<TRaw>[]
  records: TRaw[]
  aggregated: TAgg[]
  rowKey: (row: TRaw | TAgg, index: number) => string | number
}

/**
 * Shared "metrics row + Aggregated/All records toggle + table" layout used
 * identically by the Cookies and Query Params tabs (tabs/cookies.py and
 * tabs/query_params.py in the original are near-duplicates of exactly this
 * shape) -- factored out here since both call sites need it at once.
 */
export function AggregateToggleView<TRaw, TAgg>({
  title,
  metrics,
  aggregatedCaption,
  aggregatedColumns,
  rawColumns,
  records,
  aggregated,
  rowKey,
}: AggregateToggleViewProps<TRaw, TAgg>) {
  const [view, setView] = useState<'aggregated' | 'raw'>('aggregated')

  return (
    <div className="aggregate-toggle-view">
      <h3>{title}</h3>
      <div className="metrics-row">
        {metrics.map((m) => (
          <div className="metric" key={m.label}>
            <span className="metric__label">{m.label}</span>
            <span className="metric__value">{m.value.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <fieldset className="search-controls__methods">
        <legend>View</legend>
        {(['aggregated', 'raw'] as const).map((option) => (
          <label key={option} className="search-controls__checkbox">
            <input type="radio" checked={view === option} onChange={() => setView(option)} />
            {option === 'aggregated' ? 'Aggregated by name' : 'All records'}
          </label>
        ))}
      </fieldset>

      {view === 'aggregated' ? (
        <>
          <p className="overview__caption">{aggregatedCaption}</p>
          <DataTable columns={aggregatedColumns} rows={aggregated} rowKey={rowKey} />
        </>
      ) : (
        <DataTable columns={rawColumns} rows={records} rowKey={rowKey} />
      )}
    </div>
  )
}
