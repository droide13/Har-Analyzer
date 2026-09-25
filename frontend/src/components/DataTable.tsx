import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getExpandedRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type ColumnSizingState,
  type ExpandedState,
  type SortingState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'

export interface DataTableColumn<T> {
  header: string
  accessor: (row: T) => ReactNode
  /** Plain text to size the column's default width against. Only needed
   * when `accessor` renders JSX (a badge, an icon) instead of a plain
   * string/number -- without it, initial sizing would fall back to
   * stringifying the rendered element (e.g. "[object Object]") instead of
   * reflecting what's actually in the column. */
  sizingText?: (row: T) => string
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
  /** When set, a row click calls this instead of the default
   * expand/collapse toggle -- for tables that navigate to an external
   * detail view (Network Log, Dissemination) rather than expanding in
   * place. */
  onRowClick?: (row: T, index: number) => void
  /** Extra classes for a row (selection outline, search-match highlight),
   * computed per row. */
  rowClassName?: (row: T, index: number) => string
}

const MIN_CONTENT_PX = 72
const MAX_CONTENT_PX = 320
const CELL_PADDING_PX = 20
const CHARS_SAMPLED_ROWS = 200
// Initial per-row height guess for the virtualizer -- corrected per row via
// measureElement as soon as it mounts (a row can be taller than this once
// expanded), so this only has to be roughly right for the collapsed case.
const DEFAULT_ROW_HEIGHT_PX = 33
const COMPACT_ROW_HEIGHT_PX = 27
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
      const text = col.sizingText ? col.sizingText(row) : String(col.accessor(row) ?? '')
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

/** Row-virtualized (via react-virtual) so a raw, ungrouped record count in
 * the thousands (e.g. every cookie/query-param occurrence across a large
 * HAR, not just the name-grouped aggregate, or Network Log/Dissemination's
 * entry lists via EntryListTable) never mounts more <tr>s than the viewport
 * actually shows.
 *
 * Keeps a real <table> (column resize/sizing below depends on native
 * <colgroup> layout, which a <tr> can't get while absolutely positioned) --
 * only the visible slice of rows renders in normal flow, padded above/below
 * by two spacer <tr>s sized to the remaining (unrendered) scroll height.
 * This is what keeps the header and body columns pixel-aligned under
 * horizontal scroll and while an adjacent panel resizes this table's
 * container -- the two can never drift apart the way a hand-rolled flex-row
 * + position:absolute layout can. Each row's real height is remeasured once
 * mounted (measureElement), since expanding a row wraps it to multiple
 * lines -- rows aren't a fixed height.
 *
 * Column sizing/resizing and row-expansion state are delegated to
 * TanStack Table (the same maintainer/family as react-query and
 * react-virtual) rather than hand-rolled -- only the *initial* content-aware
 * widths above are custom, since no generic table library can know what "a
 * reasonable width for this data" means for a given column. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  showHeader = true,
  emptyLabel = 'No rows.',
  variant = 'default',
  onRowClick,
  rowClassName,
}: DataTableProps<T>) {
  const cellPadding = variant === 'compact' ? 'px-2 py-1 text-xs' : 'px-2 py-1 text-[13px]'
  const containerRef = useRef<HTMLDivElement>(null)
  const columnKey = columns.map((c) => c.header).join('␟')
  // Tracks whether the user has dragged a resize handle -- once they have,
  // their widths are intentional and the container-resize effect below
  // must stop overwriting them (e.g. every pixel of dragging the entry
  // detail panel's own splitter would otherwise fight a manual column
  // resize).
  const manuallyResizedRef = useRef(false)

  const [columnSizing, setColumnSizing] = useState<{ key: string; sizing: ColumnSizingState }>(() => ({
    key: columnKey,
    sizing: computeInitialSizing(columns, rows, ASSUMED_CONTAINER_PX),
  }))
  const [expanded, setExpanded] = useState<ExpandedState>({})
  const [sorting, setSorting] = useState<{ key: string; state: SortingState }>({ key: columnKey, state: [] })

  // Re-derive default widths (and clear any sort) whenever the column
  // *shape* changes (not on every row update, so pagination/filtering
  // never wipes out a resize/sort the user just made), against the
  // container's real measured width -- the very first render has to guess
  // (ASSUMED_CONTAINER_PX) since nothing is in the DOM yet, and this
  // corrects that before the browser paints.
  useLayoutEffect(() => {
    const measured = containerRef.current?.clientWidth || ASSUMED_CONTAINER_PX
    manuallyResizedRef.current = false
    setColumnSizing({ key: columnKey, sizing: computeInitialSizing(columns, rows, measured) })
    setSorting((prev) => (prev.key === columnKey ? prev : { key: columnKey, state: [] }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnKey])

  // Re-fit column widths whenever the container itself resizes -- opening
  // an adjacent detail panel or dragging its splitter changes this table's
  // available width without changing its column *shape*, so the effect
  // above (keyed only on columnKey) never re-runs for it. Only auto-fits
  // while the user hasn't manually resized a column, so this can't fight a
  // deliberate drag.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    let lastWidth = el.clientWidth
    const observer = new ResizeObserver(() => {
      const width = el.clientWidth
      if (Math.abs(width - lastWidth) < 2 || manuallyResizedRef.current) return
      lastWidth = width
      setColumnSizing({ key: columnKey, sizing: computeInitialSizing(columns, rows, width) })
    })
    observer.observe(el)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnKey])

  const colDefs: ColumnDef<T>[] = columns.map((col) => ({
    id: col.header,
    header: col.header,
    accessorFn: (row) => {
      const value = col.accessor(row)
      return typeof value === 'string' || typeof value === 'number' ? value : cellText(value)
    },
    cell: (ctx) => col.accessor(ctx.row.original),
    minSize: MIN_CONTENT_PX,
  }))

  const table = useReactTable({
    data: rows,
    columns: colDefs,
    getRowId: (row, index) => String(rowKey(row, index)),
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowCanExpand: () => true,
    columnResizeMode: 'onChange',
    enableColumnResizing: true,
    state: {
      columnSizing: columnSizing.key === columnKey ? columnSizing.sizing : computeInitialSizing(columns, rows, ASSUMED_CONTAINER_PX),
      expanded,
      sorting: sorting.key === columnKey ? sorting.state : [],
    },
    onColumnSizingChange: (updater) => {
      manuallyResizedRef.current = true
      setColumnSizing((prev) => ({
        key: columnKey,
        sizing: typeof updater === 'function' ? updater(prev.sizing) : updater,
      }))
    },
    onExpandedChange: setExpanded,
    onSortingChange: (updater) =>
      setSorting((prev) => ({
        key: columnKey,
        state: typeof updater === 'function' ? updater(prev.state) : updater,
      })),
  })

  const leafColumns = table.getAllLeafColumns()
  const tableRows = table.getRowModel().rows

  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => (variant === 'compact' ? COMPACT_ROW_HEIGHT_PX : DEFAULT_ROW_HEIGHT_PX),
    overscan: 10,
  })
  const virtualRows = virtualizer.getVirtualItems()
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0
  const paddingBottom =
    virtualRows.length > 0 ? virtualizer.getTotalSize() - virtualRows[virtualRows.length - 1].end : 0

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
                  const sortDirection = header.column.getIsSorted()
                  return (
                    <th
                      key={header.id}
                      title={colDef?.header}
                      style={{ width: header.getSize() }}
                      className={`sticky top-0 z-10 overflow-hidden border-b border-border bg-bg-subtle text-left text-ellipsis whitespace-nowrap font-medium text-text-muted ${cellPadding} ${colDef?.className ?? ''}`}
                    >
                      <span className="relative flex items-center justify-between gap-1">
                        <span
                          onClick={header.column.getToggleSortingHandler()}
                          className="flex min-w-0 cursor-pointer items-center gap-1 overflow-hidden text-ellipsis select-none hover:text-text"
                        >
                          <span className="overflow-hidden text-ellipsis">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </span>
                          <span className="shrink-0 text-[9px] text-accent">
                            {sortDirection === 'asc' ? '▲' : sortDirection === 'desc' ? '▼' : ''}
                          </span>
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
          {paddingTop > 0 && (
            <tr aria-hidden="true" style={{ height: paddingTop }}>
              <td style={{ padding: 0, border: 0 }} colSpan={leafColumns.length} />
            </tr>
          )}
          {virtualRows.map((virtualRow) => {
            const row = tableRows[virtualRow.index]
            const isExpanded = row.getIsExpanded()
            const wrap = isExpanded ? 'whitespace-normal break-words' : 'whitespace-nowrap'
            return (
              <tr
                key={row.id}
                ref={virtualizer.measureElement}
                data-index={virtualRow.index}
                onClick={() => {
                  // Selecting text (e.g. to copy a value out of an expanded
                  // row) is a mousedown-drag-mouseup sequence on the same
                  // row, which the browser still fires as a click -- act
                  // only when that click didn't leave a selection behind,
                  // so releasing the mouse to hit Ctrl+C doesn't collapse
                  // the row (or navigate away) out from under you.
                  if (window.getSelection()?.toString()) return
                  if (onRowClick) onRowClick(row.original, virtualRow.index)
                  else row.toggleExpanded()
                }}
                className={`cursor-pointer border-b border-border hover:bg-bg-subtle/60 ${isExpanded ? 'bg-bg-subtle/40' : ''} ${rowClassName ? rowClassName(row.original, virtualRow.index) : ''}`}
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
          {paddingBottom > 0 && (
            <tr aria-hidden="true" style={{ height: paddingBottom }}>
              <td style={{ padding: 0, border: 0 }} colSpan={leafColumns.length} />
            </tr>
          )}
        </tbody>
      </table>
      {rows.length === 0 && <p className="p-4 text-center text-text-muted">{emptyLabel}</p>}
    </div>
  )
}
