import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { fetchMetadata, fetchNamingOptions, generateMetadata, standardizedDownloadUrl } from '../../api/metadata'
import type { GenerateMetadataRequest } from '../../api/types'
import { Button } from '../../components/Button'
import { DataTable } from '../../components/DataTable'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { HelpText } from '../../components/HelpText'
import { MetricsRow } from '../../components/MetricsRow'
import { ErrorState, LoadingState } from '../../components/QueryState'

interface MetadataViewProps {
  uploadId: string
}

const CUSTOM_DOMAIN_LABEL = 'Custom domain...'

function firstKey(labels: Record<string, string>): string {
  return Object.keys(labels)[0] ?? ''
}

interface NamingFieldProps {
  label: string
  /** internal-code -> display-label map from /api/naming/options. */
  options: Record<string, string>
  value: string
  onChange: (value: string) => void
}

/** One of the classification dropdowns -- four of them differ only in which
 * naming-option map they list, so the select markup lives here once. */
function NamingField({ label, options, value, onChange }: NamingFieldProps) {
  return (
    <FormField label={label}>
      <select className={fieldInputClasses} value={value} onChange={(e) => onChange(e.target.value)}>
        {Object.entries(options).map(([key, optionLabel]) => (
          <option key={key} value={key}>
            {optionLabel}
          </option>
        ))}
      </select>
    </FormField>
  )
}

/** Direct port of tabs/metadata/metadata_ui.py: review detected domain/
 * capture time, confirm classification, generate a standardized copy with
 * log._analysis embedded, download it. The one write/export path in the
 * app -- generate and download are two explicit steps here too, same as
 * the original's button + frozen session-state download. */
export function MetadataView({ uploadId }: MetadataViewProps) {
  const {
    data: metadata,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['metadata', uploadId],
    queryFn: () => fetchMetadata(uploadId),
  })
  const { data: naming } = useQuery({ queryKey: ['naming-options'], queryFn: fetchNamingOptions })

  const [selectedDomainOption, setSelectedDomainOption] = useState('')
  const [customDomain, setCustomDomain] = useState('')
  const [platform, setPlatform] = useState('')
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
      setPlatform((prev) => prev || firstKey(naming.platform))
      setInteract((prev) => prev || firstKey(naming.interact))
      setCookies((prev) => prev || firstKey(naming.cookies))
      setVisit((prev) => prev || firstKey(naming.visit))
    }
  }, [metadata, naming])

  const generateMutation = useMutation({
    mutationFn: (body: GenerateMetadataRequest) => generateMetadata(uploadId, body),
    onSuccess: (_result, variables) => setLastGeneratedInputs(variables),
  })

  if (isLoading) return <LoadingState />
  if (isError) return <ErrorState label="Failed to load metadata." />
  if (!metadata || !naming) return null

  const domain = selectedDomainOption === CUSTOM_DOMAIN_LABEL ? customDomain : selectedDomainOption
  const capturedAt = metadata.detected.captured_at ?? manualCapturedAt
  const hasExisting = metadata.existing_analysis !== null
  const formVisible = !hasExisting || overwriteConfirmed

  const currentInputs: GenerateMetadataRequest = {
    domain,
    platform,
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
    <div>
      <h3 className="text-base font-semibold">Standardize &amp; Tag Current HAR File</h3>
      <HelpText>
        Domain and capture time are derived from the traffic itself, allowing you to confirm or override
        classification before generating an updated copy with embedded log._analysis metadata.
      </HelpText>

      <h4 className="text-sm font-semibold">Detected from file contents</h4>
      <MetricsRow
        metrics={[
          { label: 'Primary domain (first request)', value: metadata.detected.first_request_domain },
          {
            label: 'Capture time',
            value: metadata.detected.captured_at ? new Date(metadata.detected.captured_at).toLocaleString() : 'Unknown',
          },
        ]}
      />
      {metadata.detected.captured_at === null && (
        <ErrorState label="Could not parse a capture timestamp from any entry's startedDateTime. Enter one manually below." />
      )}

      {hasExisting && metadata.existing_analysis && (
        <>
          <h4 className="text-sm font-semibold">Current metadata</h4>
          <DataTable
            showHeader={false}
            columns={[
              { header: 'Field', accessor: ([field]) => field, className: 'font-semibold' },
              { header: 'Value', accessor: ([, value]) => String(value) },
            ]}
            rows={Object.entries(metadata.existing_analysis)}
            rowKey={([field]) => field}
          />
          <label className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
            <input type="checkbox" checked={overwriteConfirmed} onChange={(e) => setOverwriteConfirmed(e.target.checked)} />
            I want to overwrite this with new values below.
          </label>
        </>
      )}

      {formVisible && (
        <>
          <h4 className="mt-3 text-sm font-semibold">Confirm classification</h4>
          <FormRow>
            <FormField label="Domain">
              <select className={fieldInputClasses} value={selectedDomainOption} onChange={(e) => setSelectedDomainOption(e.target.value)}>
                {metadata.detected.domain_options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </FormField>
            {selectedDomainOption === CUSTOM_DOMAIN_LABEL && (
              <FormField label="Custom domain">
                <input type="text" className={fieldInputClasses} value={customDomain} onChange={(e) => setCustomDomain(e.target.value)} />
              </FormField>
            )}
            <NamingField label="Platform" options={naming.platform} value={platform} onChange={setPlatform} />
            <NamingField label="Interaction type" options={naming.interact} value={interact} onChange={setInteract} />
            <NamingField label="Cookie handling" options={naming.cookies} value={cookies} onChange={setCookies} />
          </FormRow>

          <FormRow>
            <NamingField label="Visit type" options={naming.visit} value={visit} onChange={setVisit} />
            <FormField label="Extra context (optional)">
              <input type="text" className={fieldInputClasses} value={extra} onChange={(e) => setExtra(e.target.value)} maxLength={3} />
            </FormField>
            {metadata.detected.captured_at === null && (
              <FormField label="Capture date">
                <input
                  type="datetime-local"
                  className={fieldInputClasses}
                  value={manualCapturedAt}
                  onChange={(e) => setManualCapturedAt(e.target.value)}
                />
              </FormField>
            )}
          </FormRow>

          <h4 className="text-sm font-semibold">Experiment notes</h4>
          <HelpText>Written into log._analysis inside the file itself, not just the filename.</HelpText>
          <FormRow>
            <FormField label="Description">
              <textarea className={fieldInputClasses} value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
            </FormField>
          </FormRow>
          <FormRow>
            <FormField label="Email used">
              <input type="text" className={fieldInputClasses} value={emailUsed} onChange={(e) => setEmailUsed(e.target.value)} />
            </FormField>
          </FormRow>
          <FormRow>
            <FormField label="Notes">
              <textarea className={fieldInputClasses} value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </FormField>
          </FormRow>

          <h4 className="text-sm font-semibold">Standardized Output</h4>
          <Button
            variant="primary"
            onClick={() => generateMutation.mutate(currentInputs)}
            disabled={!canGenerate || generateMutation.isPending}
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate standardized file'}
          </Button>
          {generateMutation.isError && <ErrorState label={`Failed to generate: ${String(generateMutation.error)}`} />}

          {generateMutation.data ? (
            <>
              {isStale && (
                <ErrorState label='Form values changed since this file was generated. Press "Generate standardized file" again to update the download.' />
              )}
              <p className="mt-2">
                <code>{generateMutation.data.filename}</code>
              </p>
              <p>
                <a className="text-accent underline" href={standardizedDownloadUrl(uploadId)} download={generateMutation.data.filename}>
                  Download Standardized .har
                </a>
              </p>
              <HelpText>
                Note on browser save location: web browsers determine whether files download directly or open a
                save dialog. To be prompted for a folder path on every download, enable "Ask where to save each
                file before downloading" in your browser's settings.
              </HelpText>
            </>
          ) : (
            <HelpText>Fill in the fields above and click "Generate standardized file".</HelpText>
          )}
        </>
      )}
    </div>
  )
}
