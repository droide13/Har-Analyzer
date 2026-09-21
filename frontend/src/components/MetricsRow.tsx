import type { ReactNode } from 'react'

export interface Metric {
  label: string
  value: ReactNode
}

interface MetricsRowProps {
  metrics: Metric[]
}

/** Shared "label above a big number" row -- Overview, Dissemination,
 * Metadata and AggregateToggleView each used to hand-roll the same
 * three-line block per metric. */
export function MetricsRow({ metrics }: MetricsRowProps) {
  return (
    <div className="mb-4 flex flex-wrap gap-2.5">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="flex min-w-[104px] flex-col gap-1 rounded border border-border bg-bg-subtle px-3.5 py-2.5"
        >
          <span className="text-xs text-text-muted">{metric.label}</span>
          <span className="font-mono text-[20px] leading-none font-semibold">{metric.value}</span>
        </div>
      ))}
    </div>
  )
}
