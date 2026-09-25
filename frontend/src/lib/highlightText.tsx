import type { ReactNode } from 'react'

/** Wraps every case-insensitive occurrence of `needle` in `text` with a
 * <mark> -- used by the entry detail panel to show exactly which substring
 * a Matched Fields chip jumped to a tab for. Returns `text` unchanged when
 * there's nothing to highlight or nothing found. */
export function highlightText(text: string, needle: string): ReactNode {
  if (!needle) return text
  const lower = text.toLowerCase()
  const needleLower = needle.toLowerCase()
  const firstIndex = lower.indexOf(needleLower)
  if (firstIndex === -1) return text

  const parts: ReactNode[] = []
  let cursor = 0
  let index = firstIndex
  while (index !== -1) {
    if (index > cursor) parts.push(text.slice(cursor, index))
    parts.push(
      // Fixed dark text rather than text-inherit -- in dark mode the
      // surrounding text is near-white, which barely reads against a
      // yellow wash. A <mark> is always yellow-on-dark-text regardless of
      // theme, the same convention browsers use for find-in-page.
      <mark key={index} className="rounded-sm bg-highlight-strong px-0.5 text-[#1f2328]">
        {text.slice(index, index + needle.length)}
      </mark>,
    )
    cursor = index + needle.length
    index = lower.indexOf(needleLower, cursor)
  }
  if (cursor < text.length) parts.push(text.slice(cursor))
  return parts
}
