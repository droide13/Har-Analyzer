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
