import { useState } from 'react'
import type { RootDomainMetric } from '../../api/types'
import { formatBytes } from '../../lib/formatBytes'
import { BarChart, type BarChartDatum } from '../../components/BarChart'
import { SubdomainResolution } from './SubdomainResolution'

interface DomainExplorerProps {
  uploadId: string
  domainMap: Record<string, RootDomainMetric>
  firstPartyDomain: string
}

type SortBy = 'Requests' | 'Bandwidth'

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
    <div className="domain-explorer">
      <h3>Domain and Subdomain Explorer</h3>

      <div className="search-controls__row">
        <fieldset className="search-controls__methods">
          <legend>Sort Everything By</legend>
          {(['Requests', 'Bandwidth'] as const).map((option) => (
            <label key={option} className="search-controls__checkbox">
              <input type="radio" checked={sortBy === option} onChange={() => setSortBy(option)} />
              {option}
            </label>
          ))}
        </fieldset>
        <label>
          Show Top Domains in Chart ({chartLimit})
          <input
            type="range"
            min={5}
            max={50}
            step={5}
            value={chartLimit}
            onChange={(e) => setChartLimit(Number(e.target.value))}
          />
        </label>
      </div>

      <h4>
        Top {chartLimit} Domains by {unitLabel}
      </h4>
      <BarChart data={topDomains} orientation="horizontal" valueLabel={unitLabel} />

      <label>
        Inspect Root Domain (alphabetically)
        <select value={selectedRoot} onChange={(e) => setSelectedRoot(e.target.value)}>
          {domainOptions.map((domain) => {
            const metric = domainMap[domain]
            return (
              <option key={domain} value={domain}>
                {domain} ({metric.requests} reqs | {formatBytes(metric.bytes)})
              </option>
            )
          })}
        </select>
      </label>

      {root && (
        <>
          <div className="metrics-row">
            <div className="metric">
              <span className="metric__label">Root Requests</span>
              <span className="metric__value">{root.requests.toLocaleString()}</span>
            </div>
            <div className="metric">
              <span className="metric__label">Total Bandwidth</span>
              <span className="metric__value">{formatBytes(root.bytes)}</span>
            </div>
            <div className="metric">
              <span className="metric__label">Subdomains Seen</span>
              <span className="metric__value">{Object.keys(root.subdomains).length}</span>
            </div>
          </div>

          <h4>
            Subdomains of `{selectedRoot}` (sorted by {sortBy})
          </h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Subdomain Address</th>
                <th>Requests</th>
                <th>Total Size</th>
              </tr>
            </thead>
            <tbody>
              {subdomainRows.map((row) => (
                <tr key={row.subdomain}>
                  <td>{row.subdomain}</td>
                  <td>{row.requests}</td>
                  <td>{formatBytes(row.bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedRoot === firstPartyDomain && firstPartyDomain !== 'unknown' && (
            <SubdomainResolution
              uploadId={uploadId}
              firstPartyRoot={firstPartyDomain}
              subdomains={Object.keys(root.subdomains)}
            />
          )}
        </>
      )}
    </div>
  )
}
