/** Pre-capture metadata draft, jotted down while recording a HAR (before
 * there's an upload_id to attach anything to) and consumed once by
 * MetadataView to prefill a freshly uploaded file's tagging form -- so
 * platform/interaction/ground-truth don't have to be remembered and
 * retyped after the fact. Lives in localStorage since it spans the gap
 * between "filling this in" and "uploading the resulting .har". */

import type { GroundTruthEntry } from '../api/types'

const STORAGE_KEY = 'har-analyzer:capture-draft'

export interface CaptureDraft {
  platform: string
  interact: string
  cookies: string
  visit: string
  extra: string
  description: string
  groundTruth: GroundTruthEntry[]
  notes: string
}

export function loadCaptureDraft(): CaptureDraft | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as CaptureDraft) : null
  } catch {
    return null
  }
}

export function saveCaptureDraft(draft: CaptureDraft): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft))
  } catch {
    // Best-effort -- private browsing / blocked storage just means no draft.
  }
}

export function clearCaptureDraft(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to do if storage is unavailable.
  }
}
