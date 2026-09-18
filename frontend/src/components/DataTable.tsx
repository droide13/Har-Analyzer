import type { ReactNode } from 'react'

export interface DataTableColumn<T> {
  header: string
  accessor: (row: T) => ReactNode
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T, index: number) => string | number
}

/** Plain (non-virtualized) table for record counts that don't need
 * row-level virtualization the way Network Log's full entry list does
 * (cookie/query-param occurrence counts run in the hundreds, not thousands
 * of rows with per-row detail fetches). */
export function DataTable<T>({ columns, rows, rowKey }: DataTableProps<T>) {
  return (
    <div className="data-table__scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.header}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey(row, i)}>
              {columns.map((col) => (
                <td key={col.header}>{col.accessor(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className="data-table__empty">No rows.</p>}
    </div>
  )
}
