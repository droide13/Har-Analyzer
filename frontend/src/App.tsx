import { useState } from 'react'
import { FileUpload } from './components/FileUpload'
import { PageHeader } from './components/PageHeader'
import { SessionBar } from './components/SessionBar'
import { Tabs, type TabDefinition } from './components/Tabs'
import { NetworkLogView } from './features/networkLog/NetworkLogView'
import { OverviewView } from './features/overview/OverviewView'
import { IdentifiersView } from './features/identifiers/IdentifiersView'
import { DisseminationView } from './features/dissemination/DisseminationView'
import { MetadataView } from './features/metadata/MetadataView'
import type { UploadResponse } from './api/types'

export default function App() {
  const [session, setSession] = useState<UploadResponse | null>(null)
  // True whenever the upload picker should show: always with no session
  // yet, or on demand afterward via SessionBar's "Switch file".
  const [isPickingFile, setIsPickingFile] = useState(false)
  const [activeTab, setActiveTab] = useState('network-log')
  // Set by the Identifiers tab's "Trace" button; consumed once by
  // DisseminationView to select that key and auto-run its dissemination
  // search.
  const [disseminationTarget, setDisseminationTarget] = useState<{ key: string } | null>(null)

  function handleUploaded(upload: UploadResponse) {
    setSession(upload)
    setIsPickingFile(false)
    // Mirrors the original: open straight on Metadata whenever the filename
    // doesn't follow the naming convention or the HAR hasn't been through
    // "Generate standardized file" yet, so there's an immediate nudge to fix
    // it rather than a silent Network Log view with unreadable session info.
    const { filename_valid, has_analysis } = upload.session_metadata
    setActiveTab(filename_valid && has_analysis ? 'network-log' : 'metadata')
    setDisseminationTarget(null)
  }

  function handleTraceKey(key: string) {
    setDisseminationTarget({ key })
    setActiveTab('dissemination')
  }

  const tabs: TabDefinition[] = session
    ? [
        { key: 'network-log', label: 'Network Log', render: () => <NetworkLogView uploadId={session.upload_id} /> },
        { key: 'overview', label: 'HAR Analytics', render: () => <OverviewView uploadId={session.upload_id} /> },
        {
          key: 'identifiers',
          label: 'Identifiers',
          render: () => <IdentifiersView uploadId={session.upload_id} onTraceKey={handleTraceKey} />,
        },
        {
          key: 'dissemination',
          label: 'Dissemination',
          render: () => (
            <DisseminationView
              uploadId={session.upload_id}
              initialTarget={disseminationTarget}
              onInitialTargetConsumed={() => setDisseminationTarget(null)}
            />
          ),
        },
        { key: 'metadata', label: 'Metadata', render: () => <MetadataView uploadId={session.upload_id} /> },
      ]
    : []

  return (
    <div className="mx-auto flex min-h-[100svh] w-full max-w-[1400px] flex-col gap-3 px-6 pt-4 pb-24">
      <PageHeader title="HAR Analyzer" />

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
          <Tabs
            key={session.upload_id}
            tabs={tabs}
            variant="page"
            activeTab={activeTab}
            onActiveTabChange={setActiveTab}
          />
        </>
      )}
    </div>
  )
}
