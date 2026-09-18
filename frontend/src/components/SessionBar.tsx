import type { UploadResponse } from '../api/types'

interface SessionBarProps {
  session: UploadResponse
  onSwitchFile: () => void
}

/** Persistent strip above the tabs showing which file is loaded, with a way
 * to load a different one without reloading the page -- st.file_uploader
 * let you do this for free; a React SPA needs it built explicitly. */
export function SessionBar({ session, onSwitchFile }: SessionBarProps) {
  return (
    <div className="session-bar">
      <p className="app__session-info">
        {session.filename} &mdash; {session.entry_count} entries
      </p>
      <button onClick={onSwitchFile}>Switch file</button>
    </div>
  )
}
