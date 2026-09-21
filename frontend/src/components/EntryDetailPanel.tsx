import { type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEntryDetail } from '../api/har'
import type { EntryDetail, HeaderPair } from '../api/types'
import { Button } from './Button'
import { DataTable } from './DataTable'
import { JsonBlock } from './JsonBlock'
import { ErrorState, LoadingState } from './QueryState'
import { Tabs, type TabDefinition } from './Tabs'

export interface ExtraDetailTab {
  key: string
  label: string
  render: (detail: EntryDetail) => ReactNode
}

interface EntryDetailPanelProps {
  uploadId: string
  index: number
  onClose: () => void
  /** Extra leading tabs a caller injects without forking this component --
   * mirrors the original's render_entry_expander(leading_tabs=...), used by
   * Dissemination for its "Matches" tab. */
  extraTabs?: ExtraDetailTab[]
}

type StandardTabKey = 'req-headers' | 'res-headers' | 'query' | 'cookies' | 'req-body' | 'res-body' | 'initiator' | 'timing' | 'details'

const STANDARD_TABS: { key: StandardTabKey; label: string }[] = [
  { key: 'req-headers', label: 'Request Headers' },
  { key: 'query', label: 'Query & Cookies' },
  { key: 'cookies', label: 'Cookies' },
  { key: 'res-headers', label: 'Response Headers' },
  { key: 'req-body', label: 'Post Data' },
  { key: 'res-body', label: 'Response Body' },
  { key: 'initiator', label: 'Initiator' },
  { key: 'timing', label: 'Timing' },
  { key: 'details', label: 'Details' },
]

const TIMING_PHASES = ['blocked', 'dns', 'connect', 'ssl', 'send', 'wait', 'receive'] as const

function formatDurationMs(value: number): string {
  return value >= 0 ? `${value.toFixed(1)} ms` : '—'
}

function PairTable({ pairs }: { pairs: HeaderPair[] }) {
  if (pairs.length === 0) return <p className="text-sm text-text-muted">None.</p>
  return (
    <DataTable
      variant="compact"
      showHeader={false}
      columns={[
        { header: 'Name', accessor: (p: HeaderPair) => p.name, className: 'font-semibold' },
        { header: 'Value', accessor: (p: HeaderPair) => p.value },
      ]}
      rows={pairs}
      rowKey={(p, i) => `${p.name}-${i}`}
    />
  )
}

function BodyText({ text, placeholder }: { text: string; placeholder: string }) {
  if (!text) return <p className="text-sm text-text-muted">{placeholder}</p>
  return <pre className="font-mono whitespace-pre-wrap break-all rounded bg-bg-inset p-2 text-xs">{text}</pre>
}

function InitiatorTab({ detail }: { detail: EntryDetail }) {
  return (
    <div>
      <p className="text-sm text-text-muted">Type: {detail.initiator_type}</p>
      {detail.initiator_url && <p className="text-sm text-text-muted">Source URL: {detail.initiator_url}</p>}
      {detail.initiator_stack.length === 0 ? (
        <p className="text-sm text-text-muted">No JS call stack available for this request.</p>
      ) : (
        <DataTable
          variant="compact"
          columns={[
            { header: 'Function', accessor: (f) => String(f.functionName ?? '(anonymous)') },
            { header: 'URL', accessor: (f) => String(f.url ?? '') },
            { header: 'Line', accessor: (f) => String(f.lineNumber ?? '') },
            { header: 'Column', accessor: (f) => String(f.columnNumber ?? '') },
          ]}
          rows={detail.initiator_stack}
          rowKey={(_, i) => i}
        />
      )}
    </div>
  )
}

function TimingTab({ detail }: { detail: EntryDetail }) {
  const timings = (detail.raw.timings as Record<string, number> | undefined) ?? {}
  const rows = TIMING_PHASES.filter((phase) => phase in timings).map((phase) => ({
    phase: phase[0].toUpperCase() + phase.slice(1),
    duration: formatDurationMs(timings[phase]),
  }))

  return (
    <div>
      <p className="text-sm text-text-muted">Started: {detail.started_date_time || 'Unknown'}</p>
      <p className="mb-2 text-sm text-text-muted">Total time: {formatDurationMs(detail.time_ms)}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-text-muted">No timing breakdown available for this entry.</p>
      ) : (
        <DataTable
          variant="compact"
          columns={[
            { header: 'Phase', accessor: (row) => row.phase },
            { header: 'Duration', accessor: (row) => row.duration },
          ]}
          rows={rows}
          rowKey={(row) => row.phase}
        />
      )}
    </div>
  )
}

function DetailsTab({ detail }: { detail: EntryDetail }) {
  const raw = detail.raw
  const request = (raw.request as Record<string, unknown> | undefined) ?? {}
  const response = (raw.response as Record<string, unknown> | undefined) ?? {}
  const cache = (raw.cache as Record<string, unknown> | undefined) ?? {}

  return (
    <div>
      <JsonBlock
        title="Connection"
        value={{
          'Server IP': raw.serverIPAddress ?? 'Unknown',
          Connection: raw.connection ?? 'Unknown',
          'Request HTTP Version': request.httpVersion ?? 'Unknown',
          'Response HTTP Version': response.httpVersion ?? 'Unknown',
        }}
      />
      <JsonBlock
        title="Sizes & Redirect"
        value={{
          'Request Headers Size': request.headersSize ?? -1,
          'Request Body Size': request.bodySize ?? -1,
          'Response Headers Size': detail.headers_size,
          'Response Body Size': detail.body_size,
          'Redirect URL': response.redirectURL ?? null,
        }}
      />
      {Object.keys(cache).length > 0 && <JsonBlock title="Cache" value={cache} />}
    </div>
  )
}

function StandardTabContent({ tab, detail }: { tab: StandardTabKey; detail: EntryDetail }) {
  switch (tab) {
    case 'req-headers':
      return <PairTable pairs={detail.req_headers} />
    case 'res-headers':
      return <PairTable pairs={detail.res_headers} />
    case 'query':
      return <PairTable pairs={detail.query_params} />
    case 'cookies':
      return (
        <div>
          <JsonBlock title="Request Cookies" value={detail.req_cookies} />
          <JsonBlock title="Response Cookies" value={detail.res_cookies} />
        </div>
      )
    case 'req-body':
      return <BodyText text={detail.req_body} placeholder="No request body found." />
    case 'res-body':
      return <BodyText text={detail.res_body} placeholder="No body content." />
    case 'initiator':
      return <InitiatorTab detail={detail} />
    case 'timing':
      return <TimingTab detail={detail} />
    case 'details':
      return <DetailsTab detail={detail} />
  }
}

/** Side panel for one entry's full Request/Response detail, fetched lazily
 * only when a row is opened -- replaces the original's nested
 * expander-in-expander-per-row pattern (tabs/shared/entry_render.py) with a
 * single on-demand fetch. Shared by Network Log and Dissemination. */
export function EntryDetailPanel({ uploadId, index, onClose, extraTabs = [] }: EntryDetailPanelProps) {
  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['entry-detail', uploadId, index],
    queryFn: () => fetchEntryDetail(uploadId, index),
  })

  const tabDefinitions: TabDefinition[] = detail
    ? [
        ...extraTabs.map((t) => ({ key: t.key, label: t.label, render: () => t.render(detail) })),
        ...STANDARD_TABS.map((t) => ({ key: t.key, label: t.label, render: () => <StandardTabContent tab={t.key} detail={detail} /> })),
      ]
    : []

  return (
    <aside className="fixed top-0 right-0 z-30 flex h-[100dvh] w-[420px] shrink-0 flex-col overflow-hidden border-l border-border-strong bg-bg shadow-lg">
      <div className="flex items-center justify-between border-b border-border bg-bg-subtle px-3 py-2">
        <strong className="font-mono text-[13px]">Entry #{index}</strong>
        <Button variant="ghost" onClick={onClose} aria-label="Close detail panel">
          ✕
        </Button>
      </div>

      {isLoading && (
        <div className="p-3">
          <LoadingState />
        </div>
      )}
      {error && (
        <div className="p-3">
          <ErrorState label="Failed to load entry detail." />
        </div>
      )}

      {detail && (
        <>
          {/* Capped + independently scrollable so a very long URL can't eat
              the panel's height and squeeze the tabs below out of view --
              the tabs area always keeps the rest of the panel regardless of
              how many lines this wraps to. */}
          <p className="max-h-24 shrink-0 overflow-y-auto font-mono px-3 pt-2 text-xs break-all">
            {detail.method} {detail.url}
          </p>
          <Tabs key={index} tabs={tabDefinitions} variant="panel" />
        </>
      )}
    </aside>
  )
}
