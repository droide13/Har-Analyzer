import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { fetchMetadata, fetchNamingOptions, generateMetadata, standardizedDownloadUrl } from '../../api/metadata'
import type { GenerateMetadataRequest } from '../../api/types'

interface MetadataViewProps {
  uploadId: string
}

const CUSTOM_DOMAIN_LABEL = 'Custom domain...'

function firstKey(labels: Record<string, string>): string {
  return Object.keys(labels)[0] ?? ''
}

/** Direct port of tabs/metadata/metadata_ui.py: review detected domain/
 * capture time, confirm classification, generate a standardized copy with
 * log._analysis embedded, download it. The one write/export path in the
 * app -- generate and download are two explicit steps here too, same as
 * the original's button + frozen session-state download. */
export function MetadataView({ uploadId }: MetadataViewProps) {
  const { data: metadata, isLoading } = useQuery({
    queryKey: ['metadata', uploadId],
    queryFn: () => fetchMetadata(uploadId),
  })
  const { data: naming } = useQuery({ queryKey: ['naming-options'], queryFn: fetchNamingOptions })

  const [selectedDomainOption, setSelectedDomainOption] = useState('')
  const [customDomain, setCustomDomain] = useState('')
  const [interact, setInteract] = useState('')
  const [cookies, setCookies] = useState('')
  const [visit, setVisit] = useState('')
  const [extra, setExtra] = useState('')
  const [manualCapturedAt, setManualCapturedAt] = useState('')
  const [description, setDescription] = useState('')
  const [emailUsed, setEmailUsed] = useState('')
  const [notes, setNotes] = useState('')
  const [overwriteConfirmed, setOverwriteConfirmed] = useState(false)
  const [lastGeneratedInputs, setLastGeneratedInputs] = useState<GenerateMetadataRequest | null>(null)

  // Seed form defaults once the detected/existing data and label tables load.
  useEffect(() => {
    if (metadata) {
      setSelectedDomainOption((prev) => prev || metadata.detected.domain_options[0] || '')
      setDescription(metadata.existing_analysis?.description ?? '')
      setEmailUsed(metadata.existing_analysis?.email_used ?? '')
      setNotes(metadata.existing_analysis?.notes ?? '')
    }
    if (naming) {
      setInteract((prev) => prev || firstKey(naming.interact))
      setCookies((prev) => prev || firstKey(naming.cookies))
      setVisit((prev) => prev || firstKey(naming.visit))
    }
  }, [metadata, naming])

  const generateMutation = useMutation({
    mutationFn: (body: GenerateMetadataRequest) => generateMetadata(uploadId, body),
    onSuccess: (_result, variables) => setLastGeneratedInputs(variables),
  })

  if (isLoading) return <p>Loading...</p>
  if (!metadata || !naming) return null

  const domain = selectedDomainOption === CUSTOM_DOMAIN_LABEL ? customDomain : selectedDomainOption
  const capturedAt = metadata.detected.captured_at ?? manualCapturedAt
  const hasExisting = metadata.existing_analysis !== null
  const formVisible = !hasExisting || overwriteConfirmed

  const currentInputs: GenerateMetadataRequest = {
    domain,
    interact,
    cookies,
    visit,
    extra,
    captured_at: capturedAt,
    description,
    email_used: emailUsed,
    notes,
  }
  const isStale =
    lastGeneratedInputs !== null && JSON.stringify(lastGeneratedInputs) !== JSON.stringify(currentInputs)
  const canGenerate = domain.trim().length > 0 && capturedAt.length > 0

  return (
    <div className="metadata">
      <h3>Standardize &amp; Tag Current HAR File</h3>
      <p className="caption">
        Domain and capture time are derived from the traffic itself, allowing you to confirm or override
        classification before generating an updated copy with embedded log._analysis metadata.
      </p>

      <h4>Detected from file contents</h4>
      <div className="metrics-row">
        <div className="metric">
          <span className="metric__label">Primary domain (first request)</span>
          <span className="metric__value">{metadata.detected.first_request_domain}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Capture time</span>
          <span className="metric__value">
            {metadata.detected.captured_at
              ? new Date(metadata.detected.captured_at).toLocaleString()
              : 'Unknown'}
          </span>
        </div>
      </div>
      {metadata.detected.captured_at === null && (
        <p className="error-text">
          Could not parse a capture timestamp from any entry's startedDateTime. Enter one manually below.
        </p>
      )}

      {hasExisting && metadata.existing_analysis && (
        <>
          <h4>Current metadata</h4>
          <table className="data-table">
            <tbody>
              {Object.entries(metadata.existing_analysis).map(([field, value]) => (
                <tr key={field}>
                  <td className="entry-detail__pair-name">{field}</td>
                  <td>{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <label className="search-controls__checkbox">
            <input type="checkbox" checked={overwriteConfirmed} onChange={(e) => setOverwriteConfirmed(e.target.checked)} />
            I want to overwrite this with new values below.
          </label>
        </>
      )}

      {formVisible && (
        <>
          <h4>Confirm classification</h4>
          <div className="search-controls__row">
            <label>
              Domain
              <select value={selectedDomainOption} onChange={(e) => setSelectedDomainOption(e.target.value)}>
                {metadata.detected.domain_options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            {selectedDomainOption === CUSTOM_DOMAIN_LABEL && (
              <label>
                Custom domain
                <input type="text" value={customDomain} onChange={(e) => setCustomDomain(e.target.value)} />
              </label>
            )}
            <label>
              Interaction type
              <select value={interact} onChange={(e) => setInteract(e.target.value)}>
                {Object.entries(naming.interact).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cookie handling
              <select value={cookies} onChange={(e) => setCookies(e.target.value)}>
                {Object.entries(naming.cookies).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="search-controls__row">
            <label>
              Visit type
              <select value={visit} onChange={(e) => setVisit(e.target.value)}>
                {Object.entries(naming.visit).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Extra context (optional)
              <input type="text" value={extra} onChange={(e) => setExtra(e.target.value)} maxLength={3} />
            </label>
            {metadata.detected.captured_at === null && (
              <label>
                Capture date
                <input
                  type="datetime-local"
                  value={manualCapturedAt}
                  onChange={(e) => setManualCapturedAt(e.target.value)}
                />
              </label>
            )}
          </div>

          <h4>Experiment notes</h4>
          <p className="caption">Written into log._analysis inside the file itself, not just the filename.</p>
          <div className="search-controls__row">
            <label>
              Description
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
            </label>
          </div>
          <div className="search-controls__row">
            <label>
              Email used
              <input type="text" value={emailUsed} onChange={(e) => setEmailUsed(e.target.value)} />
            </label>
          </div>
          <div className="search-controls__row">
            <label>
              Notes
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </label>
          </div>

          <h4>Standardized Output</h4>
          <button
            onClick={() => generateMutation.mutate(currentInputs)}
            disabled={!canGenerate || generateMutation.isPending}
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate standardized file'}
          </button>
          {generateMutation.isError && <p className="error-text">Failed to generate: {String(generateMutation.error)}</p>}

          {generateMutation.data ? (
            <>
              {isStale && (
                <p className="error-text">
                  Form values changed since this file was generated. Press "Generate standardized file" again to
                  update the download.
                </p>
              )}
              <code>{generateMutation.data.filename}</code>
              <p>
                <a href={standardizedDownloadUrl(uploadId)} download={generateMutation.data.filename}>
                  Download Standardized .har
                </a>
              </p>
              <p className="caption">
                Note on browser save location: web browsers determine whether files download directly or open a
                save dialog. To be prompted for a folder path on every download, enable "Ask where to save each
                file before downloading" in your browser's settings.
              </p>
            </>
          ) : (
            <p className="caption">Fill in the fields above and click "Generate standardized file".</p>
          )}
        </>
      )}
    </div>
  )
}
