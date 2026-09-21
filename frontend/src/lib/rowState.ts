/** Shared hover/highlight/selected row classes for Network Log's virtualized
 * div rows and Dissemination's plain <tr> rows -- the two table DOM
 * structures can't merge (one is virtualized, one is a real <table>), but
 * the visual row-state logic is identical, so it lives in one place. */
export function rowStateClassName(highlighted: boolean, selected: boolean): string {
  return [
    'cursor-pointer border-b border-border hover:bg-bg-subtle',
    highlighted ? 'bg-highlight' : '',
    selected ? 'outline outline-2 -outline-offset-2 outline-accent' : '',
  ]
    .filter(Boolean)
    .join(' ')
}
