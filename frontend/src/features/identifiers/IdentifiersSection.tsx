import type { IdentifierSummaryRow } from '../../api/types'

interface IdentifiersSectionProps {
  label: string
  identifiers: IdentifierSummaryRow[]
}

/** One of the two Identifiers sections (Query Parameters / Cookies): a
 * summary table plus a collapsible per-key value breakdown, mirroring the
 * original's per-key st.expander. */
export function IdentifiersSection({ label, identifiers }: IdentifiersSectionProps) {
  if (identifiers.length === 0) {
    return (
      <div>
        <h4>{label}</h4>
        <p>No matches in {label.toLowerCase()} at current filter settings.</p>
      </div>
    )
  }

  const hasScope = identifiers.some((tk) => tk.first_seen_as)

  return (
    <div>
      <h4>{label}</h4>
      <table className="data-table">
        <thead>
          <tr>
            <th>Key</th>
            {hasScope && <th>First Seen As</th>}
            <th>Appearances</th>
            <th>Unique Values</th>
            <th>Avg Length</th>
            <th>Avg Entropy</th>
            <th>Domains</th>
          </tr>
        </thead>
        <tbody>
          {identifiers.map((tk) => (
            <tr key={tk.key}>
              <td>{tk.key}</td>
              {hasScope && <td>{tk.first_seen_as}</td>}
              <td>{tk.appearances}</td>
              <td>{tk.unique_values}</td>
              <td>{tk.avg_length}</td>
              <td>{tk.avg_entropy}</td>
              <td>{tk.domains}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {identifiers.map((tk) => (
        <details key={tk.key} className="identifiers__value-expander">
          <summary>Values for `{tk.key}`</summary>
          <table className="data-table">
            <thead>
              <tr>
                <th>Value</th>
                {hasScope && <th>First Seen As</th>}
                <th>Appearances</th>
                <th>Length</th>
                <th>Entropy</th>
                <th>Domains</th>
              </tr>
            </thead>
            <tbody>
              {tk.values.map((v) => (
                <tr key={v.value}>
                  <td>{v.value}</td>
                  {hasScope && <td>{v.first_seen_as}</td>}
                  <td>{v.appearances}</td>
                  <td>{v.length}</td>
                  <td>{v.entropy}</td>
                  <td>{v.domains}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      ))}
    </div>
  )
}
