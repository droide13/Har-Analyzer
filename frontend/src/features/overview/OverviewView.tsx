import { useQuery } from '@tanstack/react-query'
import { fetchOverview } from '../../api/overview'
import { formatBytes } from '../../lib/formatBytes'
import { BarChart, type BarChartDatum } from '../../components/BarChart'
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

  if (isLoading) return <p>Loading...</p>
  if (isError || !data) return <p className="error-text">Failed to load overview.</p>

  return (
    <div className="overview">
      <h3>Metrics Summary</h3>
      <div className="metrics-row">
        <div className="metric">
          <span className="metric__label">Requests</span>
          <span className="metric__value">{data.summary.total_requests.toLocaleString()}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Size</span>
          <span className="metric__value">{formatBytes(data.summary.total_bandwidth)}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Domains</span>
          <span className="metric__value">{data.summary.unique_domains}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Avg Time</span>
          <span className="metric__value">{data.summary.avg_latency_ms.toFixed(1)} ms</span>
        </div>
      </div>

      <div className="overview__charts">
        <div>
          <h4>Methods</h4>
          <BarChart data={toChartData(data.method_counts)} />
        </div>
        <div>
          <h4>Status Codes</h4>
          <BarChart data={toChartData(data.status_counts)} />
        </div>
      </div>

      <DomainExplorer uploadId={uploadId} domainMap={data.domain_map} firstPartyDomain={data.first_party_domain} />
    </div>
  )
}
