import { type ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEntryDetail } from '../api/har'
import type { EntryDetail, HeaderPair } from '../api/types'

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
  if (pairs.length === 0) return <p className="entry-detail__empty">None.</p>
  return (
    <table className="entry-detail__pairs">
      <tbody>
        {pairs.map((p, i) => (
          <tr key={`${p.name}-${i}`}>
            <td className="entry-detail__pair-name">{p.name}</td>
            <td>{p.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function BodyText({ text, placeholder }: { text: string; placeholder: string }) {
  if (!text) return <p className="entry-detail__empty">{placeholder}</p>
  return <pre className="entry-detail__body">{text}</pre>
}

function InitiatorTab({ detail }: { detail: EntryDetail }) {
  return (
    <div>
      <p className="entry-detail__meta">Type: {detail.initiator_type}</p>
      {detail.initiator_url && <p className="entry-detail__meta">Source URL: {detail.initiator_url}</p>}
      {detail.initiator_stack.length === 0 ? (
        <p className="entry-detail__empty">No JS call stack available for this request.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Function</th>
              <th>URL</th>
              <th>Line</th>
              <th>Column</th>
            </tr>
          </thead>
          <tbody>
            {detail.initiator_stack.map((frame, i) => (
              <tr key={i}>
                <td>{String(frame.functionName ?? '(anonymous)')}</td>
                <td>{String(frame.url ?? '')}</td>
                <td>{String(frame.lineNumber ?? '')}</td>
                <td>{String(frame.columnNumber ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
      <p className="entry-detail__meta">Started: {detail.started_date_time || 'Unknown'}</p>
      <p className="entry-detail__meta">Total time: {formatDurationMs(detail.time_ms)}</p>
      {rows.length === 0 ? (
        <p className="entry-detail__empty">No timing breakdown available for this entry.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Phase</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.phase}>
                <td>{row.phase}</td>
                <td>{row.duration}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
      <h4>Connection</h4>
      <pre className="entry-detail__body">
        {JSON.stringify(
          {
            'Server IP': raw.serverIPAddress ?? 'Unknown',
            Connection: raw.connection ?? 'Unknown',
            'Request HTTP Version': request.httpVersion ?? 'Unknown',
            'Response HTTP Version': response.httpVersion ?? 'Unknown',
          },
          null,
          2,
        )}
      </pre>
      <h4>Sizes &amp; Redirect</h4>
      <pre className="entry-detail__body">
        {JSON.stringify(
          {
            'Request Headers Size': request.headersSize ?? -1,
            'Request Body Size': request.bodySize ?? -1,
            'Response Headers Size': detail.headers_size,
            'Response Body Size': detail.body_size,
            'Redirect URL': response.redirectURL ?? null,
          },
          null,
          2,
        )}
      </pre>
      {Object.keys(cache).length > 0 && (
        <>
          <h4>Cache</h4>
          <pre className="entry-detail__body">{JSON.stringify(cache, null, 2)}</pre>
        </>
      )}
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
          <h4>Request Cookies</h4>
          <pre className="entry-detail__body">{JSON.stringify(detail.req_cookies, null, 2)}</pre>
          <h4>Response Cookies</h4>
          <pre className="entry-detail__body">{JSON.stringify(detail.res_cookies, null, 2)}</pre>
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
  const allTabKeys = [...extraTabs.map((t) => t.key), ...STANDARD_TABS.map((t) => t.key)]
  const [tab, setTab] = useState(allTabKeys[0])

  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['entry-detail', uploadId, index],
    queryFn: () => fetchEntryDetail(uploadId, index),
  })

  return (
    <aside className="entry-detail">
      <div className="entry-detail__header">
        <strong>Entry #{index}</strong>
        <button onClick={onClose} aria-label="Close detail panel">
          ✕
        </button>
      </div>

      {isLoading && <p>Loading...</p>}
      {error && <p className="entry-detail__error">Failed to load entry detail.</p>}

      {detail && (
        <>
          <p className="entry-detail__url">
            {detail.method} {detail.url}
          </p>
          <div className="entry-detail__tabs" role="tablist">
            {extraTabs.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={t.key === tab}
                className={`entry-detail__tab ${t.key === tab ? 'entry-detail__tab--active' : ''}`}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
            {STANDARD_TABS.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={t.key === tab}
                className={`entry-detail__tab ${t.key === tab ? 'entry-detail__tab--active' : ''}`}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="entry-detail__content">
            {extraTabs.find((t) => t.key === tab)?.render(detail) ?? (
              <StandardTabContent tab={tab as StandardTabKey} detail={detail} />
            )}
          </div>
        </>
      )}
    </aside>
  )
}
