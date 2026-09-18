import type { UploadResponse } from '../api/types'

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

  return (
    <div className="session-bar">
      <div className="session-bar__row">
        <p className="app__session-info">
          {session.filename} &mdash; {session.entry_count} entries
        </p>
        <button onClick={onSwitchFile}>Switch file</button>
      </div>

      {meta.filename_valid ? (
        <div className="session-summary">
          <div className="session-summary__item">
            <span className="session-summary__label">Domain</span>
            <span className="session-summary__value">{meta.domain}</span>
          </div>
          <div className="session-summary__item">
            <span className="session-summary__label">Interaction Flow</span>
            <span className="session-summary__value">{meta.interaction}</span>
          </div>
          <div className="session-summary__item">
            <span className="session-summary__label">Cookie Action</span>
            <span className="session-summary__value">{meta.cookies}</span>
          </div>
          <div className="session-summary__item">
            <span className="session-summary__label">Visit Context</span>
            <span className="session-summary__value">{meta.visit}</span>
          </div>
          <div className="session-summary__item">
            <span className="session-summary__label">Capture Date</span>
            <span className="session-summary__value">{capturedAt}</span>
          </div>
          {meta.extra && (
            <div className="session-summary__item">
              <span className="session-summary__label">Extra Context</span>
              <span className="session-summary__value">{meta.extra}</span>
            </div>
          )}
        </div>
      ) : (
        <p className="caption">
          <code>{session.filename}</code> doesn't follow the naming convention, so interaction/cookie/visit
          context can't be read from it -- detected domain <strong>{meta.domain}</strong>, captured {capturedAt}.
          Use the Metadata tab to classify and export a standardized copy.
        </p>
      )}
    </div>
  )
}
