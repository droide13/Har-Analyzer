import { useEffect, useRef } from 'react'
import { highlightText } from '../lib/highlightText'

interface JsonBlockProps {
  title: string
  value: unknown
  /** Literal substring to wrap in <mark> within the printed JSON -- set by
   * the entry detail panel's Matched Fields tab when it jumps here. */
  highlight?: string
}

/** Heading + pretty-printed JSON dump -- EntryDetailPanel's Details and
 * Cookies tabs each repeated this exact heading/pre pair per section. */
export function JsonBlock({ title, value, highlight }: JsonBlockProps) {
  const ref = useRef<HTMLPreElement>(null)
  const text = JSON.stringify(value, null, 2)

  useEffect(() => {
    if (!highlight) return
    ref.current?.querySelector('mark')?.scrollIntoView({ block: 'center' })
  }, [highlight])

  return (
    <div className="mb-3">
      <h4 className="mb-1 text-[13px] font-semibold">{title}</h4>
      <pre ref={ref} className="font-mono whitespace-pre-wrap break-all rounded bg-bg-inset p-2 text-xs">
        {highlight ? highlightText(text, highlight) : text}
      </pre>
    </div>
  )
}
