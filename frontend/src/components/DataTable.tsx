import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type ColumnSizingState,
  type ExpandedState,
} from '@tanstack/react-table'

export interface DataTableColumn<T> {
  header: string
  accessor: (row: T) => ReactNode
  /** Cell/header content classes -- text alignment, mono, etc. Pass
   * `whitespace-normal break-all` here for a column that should wrap long
   * unbroken values (URLs, tokens) instead of the default single-line
   * ellipsis truncation. */
  className?: string
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T, index: number) => string | number
  /** false hides the <thead> entirely -- for key/value dumps where the
   * column header would just repeat "Key"/"Value". Resize handles need a
   * header row to live in, so columns are auto-sized but not resizable
   * when this is false. */
  showHeader?: boolean
  emptyLabel?: string
  /** 'compact' is a smaller 12px variant for tables nested inside the
   * already-dense entry detail panel. */
  variant?: 'default' | 'compact'
}

const MIN_CONTENT_PX = 72
const MAX_CONTENT_PX = 320
const CELL_PADDING_PX = 20
const CHARS_SAMPLED_ROWS = 200
// A reasonable desktop table width to size the *initial* columns against,
// used only for the very first paint before the container's real width can
// be measured (see the layout effect below, which corrects this against
// the actual container as soon as it mounts).
const ASSUMED_CONTAINER_PX = 900

/** Plain text of a cell's rendered value, for a hover tooltip -- every
 * DataTable column in this app renders a string or number, never nested
 * markup, so this is a safe, cheap coercion rather than a real
 * React-tree-to-text walk. */
function cellText(value: ReactNode): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

/** Rough per-column width from actual cell content (sampling the first N
 * rows -- plenty to represent a column's typical width without an O(n)
 * scan over huge result sets), so a table's default column widths reflect
 * what's actually in it instead of a per-call-site guess.
 *
 * Each column's share comes from its OWN content need against the
 * container width first -- not its share of every column's content
 * combined -- so one column with long values (a Value/URL/Hosts column)
 * doesn't dilute how much room short enum-like columns (Name, Method,
 * Secure...) get. Only once the total exceeds the container do the
 * long/flexible columns (the ones that hit the max-width cap) give space
 * back, so the table fills its container exactly with no default scroll.
 */
function computeInitialSizing<T>(
  columns: DataTableColumn<T>[],
  rows: T[],
  containerPx: number,
): ColumnSizingState {
  const sample = rows.slice(0, CHARS_SAMPLED_ROWS)
  const contentPx = columns.map((col) => {
    let longest = col.header.length
    for (const row of sample) {
      const text = String(col.accessor(row) ?? '')
      if (text.length > longest) longest = text.length
    }
    return Math.min(MAX_CONTENT_PX, Math.max(MIN_CONTENT_PX, longest * 7.2 + CELL_PADDING_PX))
  })

  const sizes = [...contentPx]
  const total = sizes.reduce((sum, px) => sum + px, 0) || 1
  const leftover = containerPx - total

  if (leftover >= 0) {
    // Room to spare: hand it to whichever column(s) wanted more than the
    // cap could give (the "flexible" long-text columns), or the single
    // widest column if none were capped.
    const capped = contentPx.map((px, i) => ({ i, px })).filter((d) => d.px === MAX_CONTENT_PX)
    if (capped.length > 0) {
      for (const d of capped) sizes[d.i] += leftover / capped.length
    } else {
      sizes[contentPx.indexOf(Math.max(...contentPx))] += leftover
    }
  } else {
    // Too tight for the container: shrink proportionally, but never below
    // a readable floor -- take the shortfall from whichever columns have
    // the most room above that floor first.
    for (let i = 0; i < sizes.length; i++) {
      if (sizes[i] < MIN_CONTENT_PX) sizes[i] = MIN_CONTENT_PX
    }
    const deficit = sizes.reduce((sum, px) => sum + px, 0) - containerPx
    const donors = sizes.map((px, i) => ({ i, room: px - MIN_CONTENT_PX })).filter((d) => d.room > 0)
    const donorRoom = donors.reduce((sum, d) => sum + d.room, 0)
    if (deficit > 0 && donorRoom > 0) {
      for (const d of donors) {
        sizes[d.i] -= (d.room / donorRoom) * Math.min(deficit, donorRoom)
      }
    }
  }

  // Floating-point rounding across many columns can land the sum a hair
  // over the container width -- a fraction of a pixel Chrome still treats
  // as "content overflows," painting a full (if practically empty)
  // scrollbar track. Trim any such sliver off the widest column so the
  // table never triggers one by accident.
  const overshoot = sizes.reduce((sum, px) => sum + px, 0) - containerPx
  if (overshoot > 0) {
    sizes[sizes.indexOf(Math.max(...sizes))] -= overshoot + 0.5
  }

  const sizing: ColumnSizingState = {}
  columns.forEach((col, i) => {
    sizing[col.header] = sizes[i]
  })
  return sizing
}

/** Plain (non-virtualized) table for record counts that don't need
 * row-level virtualization the way Network Log's full entry list does
 * (cookie/query-param occurrence counts run in the hundreds, not thousands
 * of rows with per-row detail fetches).
 *
 * Column sizing/resizing and row-expansion state are delegated to
 * TanStack Table (the same maintainer/family as the react-query and
 * react-virtual this app already depends on) rather than hand-rolled --
 * only the *initial* content-aware widths above are custom, since no
 * generic table library can know what "a reasonable width for this data"
 * means for a given column. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  showHeader = true,
  emptyLabel = 'No rows.',
  variant = 'default',
}: DataTableProps<T>) {
  const cellPadding = variant === 'compact' ? 'px-2 py-1 text-xs' : 'px-2 py-1 text-[13px]'
  const containerRef = useRef<HTMLDivElement>(null)
  const columnKey = columns.map((c) => c.header).join('␟')

  const [columnSizing, setColumnSizing] = useState<{ key: string; sizing: ColumnSizingState }>(() => ({
    key: columnKey,
    sizing: computeInitialSizing(columns, rows, ASSUMED_CONTAINER_PX),
  }))
  const [expanded, setExpanded] = useState<ExpandedState>({})

  // Re-derive default widths whenever the column *shape* changes (not on
  // every row update, so pagination/filtering never wipes out a resize the
  // user just made), against the container's real measured width -- the
  // very first render has to guess (ASSUMED_CONTAINER_PX) since nothing is
  // in the DOM yet, and this corrects that before the browser paints.
  useLayoutEffect(() => {
    const measured = containerRef.current?.clientWidth || ASSUMED_CONTAINER_PX
    setColumnSizing({ key: columnKey, sizing: computeInitialSizing(columns, rows, measured) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnKey])

  const colDefs: ColumnDef<T>[] = columns.map((col) => ({
    id: col.header,
    header: col.header,
    cell: (ctx) => col.accessor(ctx.row.original),
    minSize: MIN_CONTENT_PX,
  }))

  const table = useReactTable({
    data: rows,
    columns: colDefs,
    getRowId: (row, index) => String(rowKey(row, index)),
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true,
    columnResizeMode: 'onChange',
    enableColumnResizing: true,
    state: {
      columnSizing: columnSizing.key === columnKey ? columnSizing.sizing : computeInitialSizing(columns, rows, ASSUMED_CONTAINER_PX),
      expanded,
    },
    onColumnSizingChange: (updater) =>
      setColumnSizing((prev) => ({
        key: columnKey,
        sizing: typeof updater === 'function' ? updater(prev.sizing) : updater,
      })),
    onExpandedChange: setExpanded,
  })

  const leafColumns = table.getAllLeafColumns()

  return (
    <div ref={containerRef} className="mb-3 max-h-[60vh] overflow-auto rounded-md border border-border-strong shadow-sm">
      <table style={{ width: table.getTotalSize() }} className="table-fixed border-collapse">
        <colgroup>
          {leafColumns.map((col) => (
            <col key={col.id} style={{ width: col.getSize() }} />
          ))}
        </colgroup>
        {showHeader && (
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header, i) => {
                  const colDef = columns[i]
                  return (
                    <th
                      key={header.id}
                      title={colDef?.header}
                      style={{ width: header.getSize() }}
                      className={`sticky top-0 z-10 overflow-hidden border-b border-border bg-bg-subtle text-left text-ellipsis whitespace-nowrap font-medium text-text-muted ${cellPadding} ${colDef?.className ?? ''}`}
                    >
                      <span className="relative flex items-center justify-between gap-1">
                        <span className="overflow-hidden text-ellipsis">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </span>
                        {i < headerGroup.headers.length - 1 && (
                          <span
                            onMouseDown={header.getResizeHandler()}
                            onTouchStart={header.getResizeHandler()}
                            className="absolute top-1/2 -right-2 h-4 w-3 shrink-0 -translate-y-1/2 cursor-col-resize touch-none"
                            aria-hidden="true"
                          />
                        )}
                      </span>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
        )}
        <tbody>
          {table.getRowModel().rows.map((row) => {
            const isExpanded = row.getIsExpanded()
            const wrap = isExpanded ? 'whitespace-normal break-words' : 'whitespace-nowrap'
            return (
              <tr
                key={row.id}
                onClick={() => row.toggleExpanded()}
                className={`cursor-pointer border-b border-border hover:bg-bg-subtle/60 ${isExpanded ? 'bg-bg-subtle/40' : ''}`}
              >
                {row.getVisibleCells().map((cell, i) => {
                  const colDef = columns[i]
                  const value = colDef?.accessor(row.original)
                  return (
                    <td
                      key={cell.id}
                      title={isExpanded ? undefined : cellText(value) || undefined}
                      style={{ width: cell.column.getSize() }}
                      className={`overflow-hidden text-left text-ellipsis align-top ${wrap} ${cellPadding} ${colDef?.className ?? ''}`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
      {rows.length === 0 && <p className="p-4 text-center text-text-muted">{emptyLabel}</p>}
    </div>
  )
}
