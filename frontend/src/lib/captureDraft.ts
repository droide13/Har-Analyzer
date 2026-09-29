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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/** Coerce parsed JSON of unknown/possibly-stale shape (e.g. a draft saved
 * by an older build) into a well-formed CaptureDraft field-by-field,
 * instead of trusting `as CaptureDraft` and letting a missing/renamed
 * field (groundTruth in particular) surface as a crash deep in
 * GroundTruthEditor later. */
function sanitizeDraft(raw: unknown): CaptureDraft | null {
  if (!isRecord(raw)) return null
  const groundTruth = Array.isArray(raw.groundTruth)
    ? raw.groundTruth.filter(
        (g): g is GroundTruthEntry => isRecord(g) && typeof g.key === 'string' && typeof g.value === 'string',
      )
    : []
  return {
    platform: asString(raw.platform),
    interact: asString(raw.interact),
    cookies: asString(raw.cookies),
    visit: asString(raw.visit),
    extra: asString(raw.extra),
    description: asString(raw.description),
    groundTruth,
    notes: asString(raw.notes),
  }
}

export function loadCaptureDraft(): CaptureDraft | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? sanitizeDraft(JSON.parse(raw)) : null
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
