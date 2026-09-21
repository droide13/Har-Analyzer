import { useState } from 'react'
import { DataTable, type DataTableColumn } from './DataTable'
import { MetricsRow } from './MetricsRow'
import { SegmentedControl } from './SegmentedControl'

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

const VIEW_OPTIONS = [
  { value: 'aggregated', label: 'Aggregated by name' },
  { value: 'raw', label: 'All records' },
]

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
    <div className="mt-2">
      <h3 className="text-base font-semibold">{title}</h3>
      <MetricsRow metrics={metrics.map((m) => ({ label: m.label, value: m.value.toLocaleString() }))} />

      <SegmentedControl
        legend="View"
        options={VIEW_OPTIONS}
        value={view}
        onChange={(next) => setView(next as 'aggregated' | 'raw')}
      />

      {view === 'aggregated' ? (
        <>
          <p className="mt-1 mb-3 text-[13px] text-text-muted">{aggregatedCaption}</p>
          <DataTable columns={aggregatedColumns} rows={aggregated} rowKey={rowKey} />
        </>
      ) : (
        <DataTable columns={rawColumns} rows={records} rowKey={rowKey} />
      )}
    </div>
  )
}
