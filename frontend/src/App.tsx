import { useState } from 'react'
import { FileUpload } from './components/FileUpload'
import { TabShell, type TabDefinition } from './components/TabShell'
import { NetworkLogView } from './features/networkLog/NetworkLogView'
import type { UploadResponse } from './api/types'
import './App.css'

export default function App() {
  const [session, setSession] = useState<UploadResponse | null>(null)

  const tabs: TabDefinition[] = session
    ? [{ key: 'network-log', label: 'Network Log', render: () => <NetworkLogView uploadId={session.upload_id} /> }]
    : []

  return (
    <div className="app">
      <h1>HAR Analyzer</h1>

      {!session && <FileUpload onUploaded={setSession} />}

      {session && (
        <>
          <p className="app__session-info">
            {session.filename} &mdash; {session.entry_count} entries
          </p>
          <TabShell tabs={tabs} />
        </>
      )}
    </div>
  )
}
