import type { BadgeTone } from '../components/Badge'

/** Badge tone for an HTTP status: 2xx/3xx are ok, any other non-empty
 * status is an error, and an empty status (no response captured) is
 * unknown rather than an error. */
export function statusTone(status: string): BadgeTone {
  if (status.startsWith('2') || status.startsWith('3')) return 'ok'
  if (status) return 'error'
  return 'muted'
}
