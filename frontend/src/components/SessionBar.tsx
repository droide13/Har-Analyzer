import type { UploadResponse } from '../api/types'
import { Button } from './Button'

interface SessionBarProps {
  session: UploadResponse
  onSwitchFile: () => void
}

/** Persistent strip above the tabs: which file is loaded, a way to load a
 * different one without reloading the page (st.file_uploader let you do
 * this for free; a React SPA needs it built explicitly), and the session
 * metadata card the original showed above its own tabs -- domain,
 * interaction flow, cookie handling, visit context, extra context and
 * capture date, read from the filename's naming convention plus the HAR's
 * own traffic. */
export function SessionBar({ session, onSwitchFile }: SessionBarProps) {
  const meta = session.session_metadata
  const capturedAt = meta.captured_at ? new Date(meta.captured_at).toLocaleString() : 'Unknown'

  const summaryItems = meta.filename_valid
    ? [
        { label: 'Domain', value: meta.domain },
        { label: 'Platform', value: meta.platform },
        { label: 'Interaction Flow', value: meta.interaction },
        { label: 'Cookie Action', value: meta.cookies },
        { label: 'Visit Context', value: meta.visit },
        { label: 'Capture Date', value: capturedAt },
        ...(meta.extra ? [{ label: 'Extra Context', value: meta.extra }] : []),
      ]
    : []

  return (
    <div className="flex flex-col gap-2 border-b border-border py-1.5 pb-3">
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-[13px] text-text-muted">
          {session.filename} &mdash; {session.entry_count} entries
        </p>
        <Button onClick={onSwitchFile}>Switch file</Button>
      </div>

      {meta.filename_valid ? (
        <div className="flex flex-wrap gap-2">
          {summaryItems.map((item) => (
            <div
              key={item.label}
              className="flex min-w-[120px] flex-col gap-0.5 rounded-md border border-border bg-bg-subtle px-3 py-1.5 shadow-sm"
            >
              <span className="text-[11px] tracking-wide text-text-muted uppercase">{item.label}</span>
              <span className="font-mono text-sm font-semibold">{item.value}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[13px] text-text-muted">
          <code>{session.filename}</code> doesn't follow the naming convention, so interaction/cookie/visit
          context can't be read from it -- detected domain <strong>{meta.domain}</strong>, captured {capturedAt}.
          Use the Metadata tab to classify and export a standardized copy.
        </p>
      )}

      {meta.filename_valid && !meta.has_analysis && (
        <p className="text-[13px] text-text-muted">
          <code>{session.filename}</code> hasn't been through the Metadata tab yet -- use it to confirm
          classification and export a standardized copy with the analysis embedded.
        </p>
      )}
    </div>
  )
}
