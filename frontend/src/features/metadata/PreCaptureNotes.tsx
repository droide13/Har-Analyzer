import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchNamingOptions } from '../../api/metadata'
import type { GroundTruthEntry } from '../../api/types'
import { Button } from '../../components/Button'
import { Disclosure } from '../../components/Disclosure'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { HelpText } from '../../components/HelpText'
import { clearCaptureDraft, loadCaptureDraft, saveCaptureDraft, type CaptureDraft } from '../../lib/captureDraft'
import { GroundTruthEditor, NamingField, firstKey } from './fields'

const EMPTY_DRAFT: CaptureDraft = {
  platform: '',
  interact: '',
  cookies: '',
  visit: '',
  extra: '',
  description: '',
  groundTruth: [],
  notes: '',
}

/** Expandable "fill this in while you capture" panel, shown next to the
 * upload dropzone. Domain and capture time aren't here -- those are always
 * read straight out of the HAR itself on the Metadata tab -- but everything
 * a human has to remember (platform, interaction, cookie choice, the real
 * email/name typed into the form under test...) can be jotted down before
 * or during the capture instead of reconstructed from memory afterward.
 * Saved to localStorage and consumed once by MetadataView on the next
 * upload of a not-yet-tagged file, then cleared. */
export function PreCaptureNotes() {
  const { data: naming } = useQuery({ queryKey: ['naming-options'], queryFn: fetchNamingOptions })
  const [draft, setDraft] = useState<CaptureDraft>(EMPTY_DRAFT)
  const [hydrated, setHydrated] = useState(false)
  // True only once the user has actually typed/picked something -- distinct
  // from `draft` just holding naming-derived defaults. Gates persistence so
  // an untouched panel never writes a default-filled draft to storage that
  // MetadataView would then mistake for a real one and "prefill" from.
  const [dirty, setDirty] = useState(false)

  // Load whatever was saved last, once, then default the code fields once
  // naming options arrive -- mirrors MetadataView's own seeding. Neither
  // marks the draft dirty: this is restoring/defaulting state, not the
  // user expressing intent to save something.
  useEffect(() => {
    setDraft((prev) => ({ ...prev, ...loadCaptureDraft() }))
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (!naming) return
    setDraft((prev) => ({
      ...prev,
      platform: prev.platform || firstKey(naming.platform),
      interact: prev.interact || firstKey(naming.interact),
      cookies: prev.cookies || firstKey(naming.cookies),
      visit: prev.visit || firstKey(naming.visit),
    }))
  }, [naming])

  // Persist on every change, but only once initial hydration has happened
  // (otherwise the first render's empty defaults would stomp a saved draft
  // before it's read back in) and only once the user has touched something.
  useEffect(() => {
    if (!hydrated || !dirty) return
    saveCaptureDraft(draft)
  }, [draft, hydrated, dirty])

  function update<K extends keyof CaptureDraft>(key: K, value: CaptureDraft[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  function handleClear() {
    clearCaptureDraft()
    setDirty(false)
    setDraft(naming ? { ...EMPTY_DRAFT, platform: firstKey(naming.platform), interact: firstKey(naming.interact), cookies: firstKey(naming.cookies), visit: firstKey(naming.visit) } : EMPTY_DRAFT)
  }

  if (!naming) return null

  return (
    <Disclosure summary="Capture notes (optional)">
      <HelpText>
        Jot down what you're about to capture -- platform, interaction, the real email/name you're using -- before
        or while recording. It's saved in this browser and prefills the Metadata tab the next time you upload a HAR
        that hasn't been tagged yet.
      </HelpText>

      <FormRow>
        <NamingField label="Platform" options={naming.platform} value={draft.platform} onChange={(v) => update('platform', v)} />
        <NamingField label="Interaction type" options={naming.interact} value={draft.interact} onChange={(v) => update('interact', v)} />
        <NamingField label="Cookie handling" options={naming.cookies} value={draft.cookies} onChange={(v) => update('cookies', v)} />
        <NamingField label="Visit type" options={naming.visit} value={draft.visit} onChange={(v) => update('visit', v)} />
        <FormField label="Extra context (optional)">
          <input
            type="text"
            className={fieldInputClasses}
            value={draft.extra}
            onChange={(e) => update('extra', e.target.value)}
            maxLength={3}
          />
        </FormField>
      </FormRow>

      <FormRow>
        <FormField label="Description">
          <textarea
            className={fieldInputClasses}
            value={draft.description}
            onChange={(e) => update('description', e.target.value)}
            rows={2}
          />
        </FormField>
      </FormRow>

      <h4 className="text-sm font-semibold">Ground truth</h4>
      <GroundTruthEditor
        entries={draft.groundTruth}
        keyOptions={naming.ground_truth_keys}
        onChange={(entries: GroundTruthEntry[]) => update('groundTruth', entries)}
      />

      <FormRow>
        <FormField label="Notes">
          <textarea className={fieldInputClasses} value={draft.notes} onChange={(e) => update('notes', e.target.value)} rows={2} />
        </FormField>
      </FormRow>

      <Button variant="ghost" onClick={handleClear}>
        Clear notes
      </Button>
    </Disclosure>
  )
}
