/** Human-readable size, e.g. "1.5 KB". Presentation-only formatting of a
 * plain byte count the backend already computed -- not worth a round trip
 * or duplicating in both languages beyond this. */
export function formatBytes(sizeBytes: number): string {
  if (sizeBytes <= 0) return '0 B'
  const sizeNames = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(sizeBytes) / Math.log(1024))
  const value = Math.round((sizeBytes / Math.pow(1024, i)) * 100) / 100
  return `${value} ${sizeNames[i]}`
}

/** Same as formatBytes, but distinguishes "genuinely 0 bytes" from "the HAR
 * never recorded a size here" -- redirects, cached responses, and blocked/
 * challenge responses report bodySize/headersSize as -1 (unknown), which a
 * flat "0 B" would otherwise show identically to a real zero-byte transfer. */
export function formatBandwidth(sizeBytes: number, sizedRequests: number): string {
  return sizedRequests > 0 ? formatBytes(sizeBytes) : 'No size data'
}
