import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchEntryDetail } from '../../api/har'
import type { EntryDetail, HeaderPair } from '../../api/types'

interface EntryDetailPanelProps {
  uploadId: string
  index: number
  onClose: () => void
}

type DetailTabKey = 'req-headers' | 'res-headers' | 'query' | 'cookies' | 'req-body' | 'res-body'

const DETAIL_TABS: { key: DetailTabKey; label: string }[] = [
  { key: 'req-headers', label: 'Request Headers' },
  { key: 'res-headers', label: 'Response Headers' },
  { key: 'query', label: 'Query Params' },
  { key: 'cookies', label: 'Cookies' },
  { key: 'req-body', label: 'Post Data' },
  { key: 'res-body', label: 'Response Body' },
]

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

function BodyText({ text }: { text: string }) {
  if (!text) return <p className="entry-detail__empty">No body.</p>
  return <pre className="entry-detail__body">{text}</pre>
}

function DetailTabContent({ tab, detail }: { tab: DetailTabKey; detail: EntryDetail }) {
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
      return <BodyText text={detail.req_body} />
    case 'res-body':
      return <BodyText text={detail.res_body} />
  }
}

/** Side panel for one entry's full Request/Response detail, fetched lazily
 * only when a row is opened -- replaces the original's nested
 * expander-in-expander-per-row pattern with a single on-demand fetch. */
export function EntryDetailPanel({ uploadId, index, onClose }: EntryDetailPanelProps) {
  const [tab, setTab] = useState<DetailTabKey>('req-headers')

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
            {DETAIL_TABS.map((t) => (
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
            <DetailTabContent tab={tab} detail={detail} />
          </div>
        </>
      )}
    </aside>
  )
}
