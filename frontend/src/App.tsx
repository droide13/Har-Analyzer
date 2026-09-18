import { useState } from 'react'
import { FileUpload } from './components/FileUpload'
import { SessionBar } from './components/SessionBar'
import { TabShell, type TabDefinition } from './components/TabShell'
import { NetworkLogView } from './features/networkLog/NetworkLogView'
import { OverviewView } from './features/overview/OverviewView'
import { CookiesView } from './features/cookies/CookiesView'
import { QueryParamsView } from './features/queryParams/QueryParamsView'
import { IdentifiersView } from './features/identifiers/IdentifiersView'
import { DisseminationView } from './features/dissemination/DisseminationView'
import { MetadataView } from './features/metadata/MetadataView'
import type { UploadResponse } from './api/types'
import './App.css'

export default function App() {
  const [session, setSession] = useState<UploadResponse | null>(null)
  // True whenever the upload picker should show: always with no session
  // yet, or on demand afterward via SessionBar's "Switch file".
  const [isPickingFile, setIsPickingFile] = useState(false)

  function handleUploaded(upload: UploadResponse) {
    setSession(upload)
    setIsPickingFile(false)
  }

  const tabs: TabDefinition[] = session
    ? [
        { key: 'network-log', label: 'Network Log', render: () => <NetworkLogView uploadId={session.upload_id} /> },
        { key: 'overview', label: 'HAR Analytics', render: () => <OverviewView uploadId={session.upload_id} /> },
        { key: 'cookies', label: 'Cookies', render: () => <CookiesView uploadId={session.upload_id} /> },
        { key: 'query-params', label: 'Query Params', render: () => <QueryParamsView uploadId={session.upload_id} /> },
        { key: 'identifiers', label: 'Identifiers', render: () => <IdentifiersView uploadId={session.upload_id} /> },
        { key: 'dissemination', label: 'Dissemination', render: () => <DisseminationView uploadId={session.upload_id} /> },
        { key: 'metadata', label: 'Metadata', render: () => <MetadataView uploadId={session.upload_id} /> },
      ]
    : []

  return (
    <div className="app">
      <h1>HAR Analyzer</h1>

      {!session && <FileUpload onUploaded={handleUploaded} />}

      {session && (
        <>
          <SessionBar session={session} onSwitchFile={() => setIsPickingFile(true)} />

          {isPickingFile && (
            <FileUpload onUploaded={handleUploaded} onCancel={() => setIsPickingFile(false)} compact />
          )}

          {/* Keyed on upload_id so switching files remounts the whole tab
              tree -- every view's local filter/selection state resets
              instead of pointing at indices from the previous file. */}
          <TabShell key={session.upload_id} tabs={tabs} />
        </>
      )}
    </div>
  )
}
