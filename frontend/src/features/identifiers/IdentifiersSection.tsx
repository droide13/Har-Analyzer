import { useState } from 'react'
import type { IdentifierSummaryRow, IdentifierValueRow } from '../../api/types'
import { Button } from '../../components/Button'
import { DataTable, type DataTableColumn } from '../../components/DataTable'
import { Disclosure } from '../../components/Disclosure'

interface IdentifiersSectionProps {
  label: string
  identifiers: IdentifierSummaryRow[]
  onTraceKey?: (key: string) => void
}

function anchorId(label: string, key: string): string {
  return `identifier-${label.toLowerCase().replace(/\s+/g, '-')}-${encodeURIComponent(key)}`
}

/** One of the two Identifiers sections (Query Parameters / Cookies): a
 * summary table plus a collapsible per-key value breakdown, mirroring the
 * original's per-key st.expander. */
export function IdentifiersSection({ label, identifiers, onTraceKey }: IdentifiersSectionProps) {
  // Which per-key value breakdowns are expanded -- normally each Disclosure
  // owns this itself, but the summary table's "Inspect" button needs to
  // force one open (and scroll to it) from outside.
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set())

  function setKeyOpen(key: string, open: boolean) {
    setOpenKeys((prev) => {
      const next = new Set(prev)
      if (open) next.add(key)
      else next.delete(key)
      return next
    })
  }

  function revealKey(key: string) {
    setKeyOpen(key, true)
    requestAnimationFrame(() => {
      document.getElementById(anchorId(label, key))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

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
    {
      header: 'Values',
      accessor: (tk) => (
        <Button size="sm" onClick={() => revealKey(tk.key)}>
          Inspect values ↓
        </Button>
      ),
    },
  ]

  const valueColumns: DataTableColumn<IdentifierValueRow>[] = [
    { header: 'Value', accessor: (v) => v.value },
    ...(hasScope ? [{ header: 'First Seen As', accessor: (v: IdentifierValueRow) => v.first_seen_as }] : []),
    { header: 'Appearances', accessor: (v) => v.appearances },
    { header: 'Length', accessor: (v) => v.length },
    { header: 'Entropy', accessor: (v) => v.entropy },
    { header: 'Domains', accessor: (v) => v.domains },
  ]

  return (
    <div>
      <h4 className="text-sm font-semibold">{label}</h4>
      <DataTable columns={summaryColumns} rows={identifiers} rowKey={(tk) => tk.key} />

      {identifiers.map((tk) => (
        <div key={tk.key} id={anchorId(label, tk.key)} className="mb-3 text-[13px] scroll-mt-3">
          <Disclosure
            summary={`Values for \`${tk.key}\``}
            open={openKeys.has(tk.key)}
            onOpenChange={(open) => setKeyOpen(tk.key, open)}
          >
            <DataTable variant="compact" columns={valueColumns} rows={tk.values} rowKey={(v) => v.value} />
            {onTraceKey && (
              <Button size="sm" className="mt-2" onClick={() => onTraceKey(tk.key)}>
                Trace `{tk.key}` in Dissemination &rarr;
              </Button>
            )}
          </Disclosure>
        </div>
      ))}
    </div>
  )
}
