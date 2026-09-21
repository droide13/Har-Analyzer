import { useState } from 'react'
import type { RootDomainMetric } from '../../api/types'
import { formatBandwidth } from '../../lib/formatBytes'
import { BarChart, type BarChartDatum } from '../../components/BarChart'
import { DataTable } from '../../components/DataTable'
import { FormRow } from '../../components/FormField'
import { MetricsRow } from '../../components/MetricsRow'
import { RangeField } from '../../components/RangeField'
import { Select } from '../../components/Select'
import { SegmentedControl } from '../../components/SegmentedControl'
import { SubdomainResolution } from './SubdomainResolution'

interface DomainExplorerProps {
  uploadId: string
  domainMap: Record<string, RootDomainMetric>
  firstPartyDomain: string
}

type SortBy = 'Requests' | 'Bandwidth'

const SORT_OPTIONS = [
  { value: 'Requests', label: 'Requests' },
  { value: 'Bandwidth', label: 'Bandwidth' },
]

function metricValue(metric: { requests: number; bytes: number }, sortBy: SortBy): number {
  return sortBy === 'Requests' ? metric.requests : metric.bytes
}

/** Root/subdomain traffic breakdown, defaulting to the first-party domain.
 * The domain map is small (bounded by distinct domains), so sort/limit/
 * drill-down here are all plain client-side derivations of one payload --
 * no extra round trip per slider tweak. */
export function DomainExplorer({ uploadId, domainMap, firstPartyDomain }: DomainExplorerProps) {
  const domainOptions = Object.keys(domainMap).sort()
  const [sortBy, setSortBy] = useState<SortBy>('Requests')
  const [chartLimit, setChartLimit] = useState(10)
  const [selectedRoot, setSelectedRoot] = useState(
    domainOptions.includes(firstPartyDomain) ? firstPartyDomain : (domainOptions[0] ?? ''),
  )

  if (domainOptions.length === 0) return <p>No domain logs available.</p>

  const unitLabel = sortBy === 'Requests' ? 'Total Requests' : 'Total Bytes'
  const topDomains: BarChartDatum[] = [...domainOptions]
    .sort((a, b) => metricValue(domainMap[b], sortBy) - metricValue(domainMap[a], sortBy))
    .slice(0, chartLimit)
    .map((domain) => ({ label: domain, value: metricValue(domainMap[domain], sortBy) }))
    .reverse() // horizontal bar chart reads bottom-to-top

  const root = domainMap[selectedRoot]
  const subdomainRows = root
    ? Object.entries(root.subdomains)
        .map(([subdomain, metric]) => ({ subdomain, ...metric }))
        .sort((a, b) => metricValue(b, sortBy) - metricValue(a, sortBy))
    : []

  return (
    <div className="mt-4">
      <h3 className="text-base font-semibold">Domain and Subdomain Explorer</h3>

      <FormRow>
        <SegmentedControl legend="Sort Everything By" options={SORT_OPTIONS} value={sortBy} onChange={(v) => setSortBy(v as SortBy)} />
        <RangeField
          label="Show Top Domains in Chart"
          value={chartLimit}
          min={5}
          max={50}
          step={5}
          onChange={setChartLimit}
        />
      </FormRow>

      <h4 className="text-sm font-semibold">
        Top {chartLimit} Domains by {unitLabel}
      </h4>
      <BarChart data={topDomains} orientation="horizontal" valueLabel={unitLabel} />

      <label className="mt-3 mb-3 flex max-w-md flex-col gap-1 text-[13px] text-text-muted">
        Inspect Root Domain (alphabetically)
        <Select value={selectedRoot} onChange={setSelectedRoot} options={domainOptions} ariaLabel="Root domain" />
      </label>

      {root && (
        <>
          <MetricsRow
            metrics={[
              { label: 'Root Requests', value: root.requests.toLocaleString() },
              { label: 'Total Bandwidth', value: formatBandwidth(root.bytes, root.sized_requests) },
              { label: 'Subdomains Seen', value: Object.keys(root.subdomains).length },
            ]}
          />

          <h4 className="text-sm font-semibold">
            Subdomains of `{selectedRoot}` (sorted by {sortBy})
          </h4>
          <DataTable
            columns={[
              { header: 'Subdomain Address', accessor: (row) => row.subdomain },
              { header: 'Requests', accessor: (row) => row.requests },
              { header: 'Total Size', accessor: (row) => formatBandwidth(row.bytes, row.sized_requests) },
            ]}
            rows={subdomainRows}
            rowKey={(row) => row.subdomain}
          />

          {selectedRoot !== 'unknown' && (
            <SubdomainResolution uploadId={uploadId} rootDomain={selectedRoot} subdomains={Object.keys(root.subdomains)} />
          )}
        </>
      )}
    </div>
  )
}
