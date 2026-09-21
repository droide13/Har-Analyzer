import { useQuery } from '@tanstack/react-query'
import { fetchOverview } from '../../api/overview'
import { formatBandwidth } from '../../lib/formatBytes'
import { BarChart, type BarChartDatum } from '../../components/BarChart'
import { MetricsRow } from '../../components/MetricsRow'
import { ErrorState, LoadingState } from '../../components/QueryState'
import { DomainExplorer } from './DomainExplorer'

interface OverviewViewProps {
  uploadId: string
}

function toChartData(counts: Record<string, number>): BarChartDatum[] {
  return Object.entries(counts).map(([label, value]) => ({ label, value }))
}

/** Direct port of tabs/overview/overview_ui.py: summary metrics, method/status
 * distribution, and the domain/subdomain explorer. */
export function OverviewView({ uploadId }: OverviewViewProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['overview', uploadId],
    queryFn: () => fetchOverview(uploadId),
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState label="Failed to load overview." />

  return (
    <div>
      <h3 className="text-base font-semibold">Metrics Summary</h3>
      <MetricsRow
        metrics={[
          { label: 'Requests', value: data.summary.total_requests.toLocaleString() },
          { label: 'Size', value: formatBandwidth(data.summary.total_bandwidth, data.summary.sized_requests) },
          { label: 'Domains', value: data.summary.unique_domains },
          { label: 'Avg Time', value: `${data.summary.avg_latency_ms.toFixed(1)} ms` },
        ]}
      />

      <div className="mb-4 grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-semibold">Methods</h4>
          <BarChart data={toChartData(data.method_counts)} />
        </div>
        <div>
          <h4 className="text-sm font-semibold">Status Codes</h4>
          <BarChart data={toChartData(data.status_counts)} />
        </div>
      </div>

      <DomainExplorer uploadId={uploadId} domainMap={data.domain_map} firstPartyDomain={data.first_party_domain} />
    </div>
  )
}
