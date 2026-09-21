import type { IdentifierSummaryRow } from '../../api/types'
import { Button } from '../../components/Button'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { Disclosure } from '../../components/Disclosure'

interface IdentifiersSectionProps {
  label: string
  identifiers: IdentifierSummaryRow[]
  onTraceValue?: (key: string, value: string) => void
}

/** One of the two Identifiers sections (Query Parameters / Cookies): a
 * summary table plus a collapsible per-key value breakdown, mirroring the
 * original's per-key st.expander. */
export function IdentifiersSection({ label, identifiers, onTraceValue }: IdentifiersSectionProps) {
  if (identifiers.length === 0) {
    return (
      <div>
        <h4 className="text-sm font-semibold">{label}</h4>
        <p className="text-[13px] text-text-muted">No matches in {label.toLowerCase()} at current filter settings.</p>
      </div>
    )
  }

  const hasScope = identifiers.some((tk) => tk.first_seen_as)

  const summaryColumns: DataTableColumn<IdentifierSummaryRow>[] = [
    { header: 'Key', accessor: (tk) => tk.key },
    ...(hasScope ? [{ header: 'First Seen As', accessor: (tk: IdentifierSummaryRow) => tk.first_seen_as }] : []),
    { header: 'Appearances', accessor: (tk) => tk.appearances },
    { header: 'Unique Values', accessor: (tk) => tk.unique_values },
    { header: 'Avg Length', accessor: (tk) => tk.avg_length },
    { header: 'Avg Entropy', accessor: (tk) => tk.avg_entropy },
    { header: 'Domains', accessor: (tk) => tk.domains },
  ]

  return (
    <div>
      <h4 className="text-sm font-semibold">{label}</h4>
      <DataTable columns={summaryColumns} rows={identifiers} rowKey={(tk) => tk.key} />

      {identifiers.map((tk) => (
        <div key={tk.key} className="mb-3 text-[13px]">
          <Disclosure summary={`Values for \`${tk.key}\``}>
            <DataTable
              variant="compact"
              columns={[
                { header: 'Value', accessor: (v: IdentifierSummaryRow['values'][number]) => v.value },
                ...(hasScope
                  ? [
                      {
                        header: 'First Seen As',
                        accessor: (v: IdentifierSummaryRow['values'][number]) => v.first_seen_as,
                      },
                    ]
                  : []),
                {
                  header: 'Appearances',
                  accessor: (v: IdentifierSummaryRow['values'][number]) => v.appearances,
                },
                { header: 'Length', accessor: (v: IdentifierSummaryRow['values'][number]) => v.length },
                {
                  header: 'Entropy',
                  accessor: (v: IdentifierSummaryRow['values'][number]) => v.entropy,
                },
                { header: 'Domains', accessor: (v: IdentifierSummaryRow['values'][number]) => v.domains },
                ...(onTraceValue
                  ? [
                      {
                        header: 'Dissemination',
                        accessor: (v: IdentifierSummaryRow['values'][number]) => (
                          <Button
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              onTraceValue(tk.key, v.value)
                            }}
                          >
                            Trace &rarr;
                          </Button>
                        ),
                      },
                    ]
                  : []),
              ]}
              rows={tk.values}
              rowKey={(v) => v.value}
            />
          </Disclosure>
        </div>
      ))}
    </div>
  )
}
