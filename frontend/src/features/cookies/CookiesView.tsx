import { useQuery } from '@tanstack/react-query'
import { fetchCookies } from '../../api/cookies'
import { AggregateToggleView } from '../../components/AggregateToggleView'
import type { DataTableColumn } from '../../components/DataTable'

interface CookiesViewProps {
  uploadId: string
}

/** Shapes of the plain dict rows backend/app/features/cookies.py returns --
 * documented here rather than typed at the API layer, since the backend
 * response is intentionally a loose dict (see RecordsView). */
interface CookieRecord {
  Name: string
  Value: string
  Scope: string
  Secure: boolean
  HttpOnly: boolean
  Host: string
}

interface CookieAggregate {
  Name: string
  'First Seen As': string
  Scope: string
  Secure: string
  HttpOnly: string
  Value: string
  Occurrences: number
  Hosts: string
}

const AGGREGATED_COLUMNS: DataTableColumn<CookieAggregate>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'First Seen As', accessor: (r) => r['First Seen As'] },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Secure', accessor: (r) => r.Secure },
  { header: 'HttpOnly', accessor: (r) => r.HttpOnly },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Occurrences', accessor: (r) => r.Occurrences },
  { header: 'Hosts', accessor: (r) => r.Hosts },
]

const RAW_COLUMNS: DataTableColumn<CookieRecord>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Scope', accessor: (r) => r.Scope },
  { header: 'Secure', accessor: (r) => String(r.Secure) },
  { header: 'HttpOnly', accessor: (r) => String(r.HttpOnly) },
  { header: 'Host', accessor: (r) => r.Host },
]

/** Direct port of tabs/cookies.py. */
export function CookiesView({ uploadId }: CookiesViewProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['cookies', uploadId],
    queryFn: () => fetchCookies(uploadId),
  })

  if (isLoading) return <p>Loading...</p>
  if (isError || !data) return <p className="overview__error">Failed to load cookies.</p>

  if (data.records.length === 0) {
    return <p>No active authentication headers or session tokens found.</p>
  }

  return (
    <AggregateToggleView<CookieRecord, CookieAggregate>
      title="Cookies list"
      metrics={[
        { label: 'Total Cookies', value: data.metrics.total },
        { label: 'Insecure SSL Cookies', value: data.metrics.missing_secure },
        { label: 'Missing HttpOnly Protection', value: data.metrics.missing_http_only },
      ]}
      aggregatedCaption="One row per cookie name. Secure/HttpOnly show 'Mixed' if they vary across occurrences; Value shows the shared value or how many distinct values were seen."
      aggregatedColumns={AGGREGATED_COLUMNS}
      rawColumns={RAW_COLUMNS}
      records={data.records as unknown as CookieRecord[]}
      aggregated={data.aggregated as unknown as CookieAggregate[]}
      rowKey={(row, i) => `${'Name' in row ? row.Name : i}-${i}`}
    />
  )
}
