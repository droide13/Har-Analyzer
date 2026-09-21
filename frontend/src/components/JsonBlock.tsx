interface JsonBlockProps {
  title: string
  value: unknown
}

/** Heading + pretty-printed JSON dump -- EntryDetailPanel's Details and
 * Cookies tabs each repeated this exact heading/pre pair per section. */
export function JsonBlock({ title, value }: JsonBlockProps) {
  return (
    <div className="mb-3">
      <h4 className="mb-1 text-[13px] font-semibold">{title}</h4>
      <pre className="font-mono whitespace-pre-wrap break-all rounded bg-bg-inset p-2 text-xs">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  )
}
