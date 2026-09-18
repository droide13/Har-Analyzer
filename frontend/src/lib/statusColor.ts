/** CSS class for an HTTP status badge: 2xx/3xx are ok, any other non-empty
 * status is an error, and an empty status (no response captured) is
 * unknown rather than an error. */
export function statusColor(status: string): string {
  if (status.startsWith('2') || status.startsWith('3')) return 'status-ok'
  if (status) return 'status-error'
  return 'status-unknown'
}
