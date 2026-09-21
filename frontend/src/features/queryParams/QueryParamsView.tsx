import { useQuery } from '@tanstack/react-query'
import { fetchQueryParams } from '../../api/queryParams'
import { AggregateToggleView } from '../../components/AggregateToggleView'
import type { DataTableColumn } from '../../components/DataTable'
import { ErrorState, LoadingState } from '../../components/QueryState'

interface QueryParamsViewProps {
  uploadId: string
}

/** Shapes of the plain dict rows backend/app/features/query_params.py
 * returns -- see the same note in CookiesView.tsx. */
interface QueryParamRecord {
  Name: string
  Value: string
  Method: string
  Host: string
}

interface QueryParamAggregate {
  Name: string
  Method: string
  Value: string
  Occurrences: number
  Hosts: string
}

const AGGREGATED_COLUMNS: DataTableColumn<QueryParamAggregate>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Method', accessor: (r) => r.Method },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Occurrences', accessor: (r) => r.Occurrences },
  { header: 'Hosts', accessor: (r) => r.Hosts },
]

const RAW_COLUMNS: DataTableColumn<QueryParamRecord>[] = [
  { header: 'Name', accessor: (r) => r.Name },
  { header: 'Value', accessor: (r) => r.Value },
  { header: 'Method', accessor: (r) => r.Method },
  { header: 'Host', accessor: (r) => r.Host },
]

/** Direct port of tabs/query_params.py. */
export function QueryParamsView({ uploadId }: QueryParamsViewProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['query-params', uploadId],
    queryFn: () => fetchQueryParams(uploadId),
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState label="Failed to load query parameters." />

  if (data.records.length === 0) {
    return <p>No query string parameters found.</p>
  }

  return (
    <AggregateToggleView<QueryParamRecord, QueryParamAggregate>
      title="Query Parameters list"
      metrics={[
        { label: 'Total Params', value: data.metrics.total },
        { label: 'Unique Param Names', value: data.metrics.unique_names },
        { label: 'Empty Values', value: data.metrics.empty_values },
      ]}
      aggregatedCaption="One row per param name. Method lists every HTTP method the param appeared under; Value shows the shared value or how many distinct values were seen."
      aggregatedColumns={AGGREGATED_COLUMNS}
      rawColumns={RAW_COLUMNS}
      records={data.records as unknown as QueryParamRecord[]}
      aggregated={data.aggregated as unknown as QueryParamAggregate[]}
      rowKey={(row, i) => `${'Name' in row ? row.Name : i}-${i}`}
    />
  )
}
