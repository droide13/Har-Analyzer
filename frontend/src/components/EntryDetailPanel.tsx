import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEntryDetail } from '../api/har'
import type { EntryBadge, EntryDetail, HeaderPair } from '../api/types'
import { Badge } from './Badge'
import { Button } from './Button'
import { DataTable } from './DataTable'
import { JsonBlock } from './JsonBlock'
import { ErrorState, LoadingState } from './QueryState'
import { Tabs, type TabDefinition } from './Tabs'
import { highlightText } from '../lib/highlightText'

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
  /** The row's own search-match badges (Network Log's Filtered/Highlighted-
   * via, Dissemination's match reasons) -- powers the "Matched Fields" tab
   * below, which shows them uncut (the table row's badges truncate) and
   * jumps to + highlights the matched text in its actual field's tab. */
  badges?: EntryBadge[]
}

type StandardTabKey = 'req-headers' | 'res-headers' | 'query' | 'cookies' | 'req-body' | 'res-body' | 'initiator' | 'timing' | 'details'

const STANDARD_TABS: { key: StandardTabKey; label: string }[] = [
  { key: 'req-headers', label: 'Request Headers' },
  { key: 'query', label: 'Query Params' },
  { key: 'cookies', label: 'Cookies' },
  { key: 'res-headers', label: 'Response Headers' },
  { key: 'req-body', label: 'Post Data' },
  { key: 'res-body', label: 'Response Body' },
  { key: 'initiator', label: 'Initiator' },
  { key: 'timing', label: 'Timing' },
  { key: 'details', label: 'Details' },
]

// Which standard tab a matched field's backend attribute (see
// backend/app/shared/search.py's ATTR_LABELS) lives in -- a field left out
// here (url, domain, method, status, mime) is already visible elsewhere in
// the panel (the top URL bar, the row itself), so its match chip isn't made
// clickable.
const ATTR_TO_TAB: Partial<Record<string, StandardTabKey>> = {
  req_headers_text: 'req-headers',
  res_headers_text: 'res-headers',
  req_body: 'req-body',
  res_body: 'res-body',
  cookies_text: 'cookies',
  query_params_text: 'query',
}

const TIMING_PHASES = ['blocked', 'dns', 'connect', 'ssl', 'send', 'wait', 'receive'] as const

function formatDurationMs(value: number): string {
  return value >= 0 ? `${value.toFixed(1)} ms` : '—'
}

/** Scrolls the first <mark> under `ref` into view whenever `text` changes --
 * shared by BodyText and JsonBlock so jumping to a match via the Matched
 * Fields tab doesn't leave the highlight scrolled out of sight below a long
 * body/JSON dump. */
function useScrollToMark(ref: RefObject<HTMLElement | null>, text: string) {
  useEffect(() => {
    if (!text) return
    ref.current?.querySelector('mark')?.scrollIntoView({ block: 'center' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])
}

function PairTable({ pairs, highlight }: { pairs: HeaderPair[]; highlight?: string }) {
  if (pairs.length === 0) return <p className="text-sm text-text-muted">None.</p>
  const needle = highlight?.toLowerCase()
  return (
    <DataTable
      variant="compact"
      showHeader={false}
      columns={[
        {
          header: 'Name',
          accessor: (p: HeaderPair) => (highlight ? highlightText(p.name, highlight) : p.name),
          sizingText: (p) => p.name,
          className: 'font-semibold',
        },
        {
          header: 'Value',
          accessor: (p: HeaderPair) => (highlight ? highlightText(p.value, highlight) : p.value),
          sizingText: (p) => p.value,
        },
      ]}
      rows={pairs}
      rowKey={(p, i) => `${p.name}-${i}`}
      rowClassName={
        needle
          ? (p) => (p.name.toLowerCase().includes(needle) || p.value.toLowerCase().includes(needle) ? 'bg-highlight/60' : '')
          : undefined
      }
    />
  )
}

function BodyText({ text, placeholder, highlight }: { text: string; placeholder: string; highlight?: string }) {
  const ref = useRef<HTMLPreElement>(null)
  useScrollToMark(ref, highlight ?? '')
  if (!text) return <p className="text-sm text-text-muted">{placeholder}</p>
  return (
    <pre ref={ref} className="font-mono whitespace-pre-wrap break-all rounded bg-bg-inset p-2 text-xs">
      {highlight ? highlightText(text, highlight) : text}
    </pre>
  )
}

function InitiatorTab({ detail }: { detail: EntryDetail }) {
  return (
    <div>
      <p className="text-sm text-text-muted">
        Type: <span className="font-mono text-text">{detail.initiator_type}</span>
      </p>
      {detail.initiator_url && (
        <p className="text-sm text-text-muted break-all">
          Source URL: <span className="font-mono text-text">{detail.initiator_url}</span>
        </p>
      )}
      {detail.initiator_stack.length === 0 ? (
        <p className="text-sm text-text-muted">No JS call stack available for this request.</p>
      ) : (
        <DataTable
          variant="compact"
          columns={[
            { header: 'Function', accessor: (f) => String(f.functionName ?? '(anonymous)'), className: 'font-mono' },
            { header: 'URL', accessor: (f) => String(f.url ?? ''), className: 'font-mono' },
            { header: 'Line', accessor: (f) => String(f.lineNumber ?? ''), className: 'font-mono' },
            { header: 'Column', accessor: (f) => String(f.columnNumber ?? ''), className: 'font-mono' },
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

/** Full, un-truncated list of every field this entry matched, across both
 * Filtered-via and Highlighted-via (Network Log) or the single match-reason
 * list (Dissemination) -- the table row's own badges only show as much as
 * fits before wrapping/truncating. A field that lives in one of the panel's
 * own tabs (headers, cookies, query params, bodies) is clickable: it jumps
 * there and highlights the literal text that matched. */
function MatchedFieldsTab({ badges, onJump }: { badges: EntryBadge[]; onJump: (attr: string, text: string) => void }) {
  const seen = new Map<string, { tone: EntryBadge['tone']; attr: string; label: string; text: string }>()
  for (const badge of badges) {
    for (const match of badge.matches) {
      seen.set(`${match.attr}::${match.text}`, { tone: badge.tone, attr: match.attr, label: match.label, text: match.text })
    }
  }
  const matches = [...seen.values()]

  if (matches.length === 0) {
    return <p className="text-sm text-text-muted">No structured match info for this entry.</p>
  }

  return (
    <div className="flex flex-col gap-2">
      {matches.map((match) => {
        const navigable = Boolean(ATTR_TO_TAB[match.attr])
        return (
          <button
            key={`${match.attr}::${match.text}`}
            type="button"
            disabled={!navigable}
            onClick={() => onJump(match.attr, match.text)}
            className={`flex flex-col items-start gap-0.5 rounded-md border border-border p-2 text-left ${navigable ? 'cursor-pointer hover:border-accent hover:bg-bg-subtle' : 'cursor-default'}`}
          >
            <Badge tone={match.tone}>{match.label}</Badge>
            <span className="font-mono text-xs break-all text-text">{match.text}</span>
          </button>
        )
      })}
    </div>
  )
}

function StandardTabContent({ tab, detail, highlight }: { tab: StandardTabKey; detail: EntryDetail; highlight?: string }) {
  switch (tab) {
    case 'req-headers':
      return <PairTable pairs={detail.req_headers} highlight={highlight} />
    case 'res-headers':
      return <PairTable pairs={detail.res_headers} highlight={highlight} />
    case 'query':
      return <PairTable pairs={detail.query_params} highlight={highlight} />
    case 'cookies':
      return (
        <div>
          <JsonBlock title="Request Cookies" value={detail.req_cookies} highlight={highlight} />
          <JsonBlock title="Response Cookies" value={detail.res_cookies} highlight={highlight} />
        </div>
      )
    case 'req-body':
      return <BodyText text={detail.req_body} placeholder="No request body found." highlight={highlight} />
    case 'res-body':
      return <BodyText text={detail.res_body} placeholder="No body content." highlight={highlight} />
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
export function EntryDetailPanel({ uploadId, index, onClose, extraTabs = [], badges = [] }: EntryDetailPanelProps) {
  // Keeps the previous entry's detail on screen (instead of `detail`
  // briefly going undefined) while the new one loads -- without this, the
  // `detail && <Tabs .../>` block below unmounts and remounts Tabs on every
  // entry switch, and a freshly-mounted Tabs always resets to its first tab.
  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['entry-detail', uploadId, index],
    queryFn: () => fetchEntryDetail(uploadId, index),
    placeholderData: (previous) => previous,
  })

  // Lifted above the `detail &&` gate (rather than left to Tabs' own
  // internal state) as a second guard: even if `detail` does go briefly
  // undefined for some other reason, the chosen tab survives.
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined)
  // Which tab + literal substring a Matched Fields chip jumped to, so that
  // tab's content can highlight it -- cleared implicitly by just not
  // matching once the user navigates to a different tab on their own.
  const [highlight, setHighlight] = useState<{ tab: StandardTabKey; text: string } | null>(null)

  function jumpToMatch(attr: string, text: string) {
    const tab = ATTR_TO_TAB[attr]
    if (!tab) return
    setHighlight({ tab, text })
    setActiveTab(tab)
  }

  const hasMatches = badges.some((b) => b.matches.length > 0)

  const tabDefinitions: TabDefinition[] = detail
    ? [
        ...extraTabs.map((t) => ({ key: t.key, label: t.label, render: () => t.render(detail) })),
        ...(hasMatches
          ? [{ key: 'matched-fields', label: 'Matched Fields', render: () => <MatchedFieldsTab badges={badges} onJump={jumpToMatch} /> }]
          : []),
        ...STANDARD_TABS.map((t) => ({
          key: t.key,
          label: t.label,
          render: () => <StandardTabContent tab={t.key} detail={detail} highlight={highlight?.tab === t.key ? highlight.text : undefined} />,
        })),
      ]
    : []

  return (
    <aside className="flex h-full w-full flex-col overflow-hidden border-l border-border-strong bg-bg">
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
          <p className="max-h-40 shrink-0 overflow-y-auto font-mono px-3 pt-2 text-[13px] leading-normal break-all">
            {detail.method} {detail.url}
          </p>
          {/* Controlled (not left to Tabs' own state) so switching to a
              different entry keeps whichever tab was open (e.g. still on
              Cookies) instead of resetting to the first one every time. */}
          <Tabs
            tabs={tabDefinitions}
            variant="panel"
            activeTab={activeTab ?? tabDefinitions[0]?.key}
            onActiveTabChange={setActiveTab}
          />
        </>
      )}
    </aside>
  )
}
