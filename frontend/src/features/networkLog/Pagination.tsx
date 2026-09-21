import { Button } from '../../components/Button'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  /** 1-indexed page numbers containing a highlighted match, across the
   * whole filtered set. Renders a row of jump buttons below Prev/Next when
   * non-empty, mirroring the original's per-page highlight jump row. */
  highlightedPages?: number[]
}

export function Pagination({ page, totalPages, onPageChange, highlightedPages = [] }: PaginationProps) {
  return (
    <div className="mb-2 flex flex-col gap-2 text-[13px]">
      <div className="flex items-center gap-3">
        <Button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <span>
          Page {page} of {totalPages}
        </span>
        <Button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
        </Button>
      </div>

      {highlightedPages.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-text-muted">
          <span>
            Highlighted on {highlightedPages.length} page{highlightedPages.length === 1 ? '' : 's'}:
          </span>
          {highlightedPages.map((p) => (
            <Button
              key={p}
              size="sm"
              variant={p === page ? 'primary' : 'secondary'}
              disabled={p === page}
              onClick={() => onPageChange(p)}
            >
              {p}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
