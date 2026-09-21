import { Button } from '../../components/Button'

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  return (
    <div className="mb-2 flex items-center gap-3 text-[13px]">
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
  )
}
