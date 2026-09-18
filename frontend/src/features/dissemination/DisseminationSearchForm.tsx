import { useEffect, useState } from 'react'

interface DisseminationSearchFormProps {
  encodingOptions: string[]
  onSearch: (encodings: string[]) => void
}

/**
 * Encoding checkboxes + explicit submit, mirroring the original's
 * st.form: ticking/unticking a box costs nothing here (no query fires)
 * until "Search dissemination" is clicked -- unlike Network Log's
 * always-live filter controls.
 */
export function DisseminationSearchForm({ encodingOptions, onSearch }: DisseminationSearchFormProps) {
  const [draftEncodings, setDraftEncodings] = useState<Set<string>>(new Set())

  // All checked by default, matching the original -- set once options load.
  useEffect(() => {
    setDraftEncodings(new Set(encodingOptions))
  }, [encodingOptions])

  function toggle(name: string) {
    const next = new Set(draftEncodings)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    setDraftEncodings(next)
  }

  return (
    <form
      className="search-controls"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch([...draftEncodings])
      }}
    >
      <p className="caption">
        This scans every field of every entry and is not run automatically. Untick any encoded/hashed forms you
        don't want, then click Search.
      </p>
      <details>
        <summary>Encodings &amp; Hashes for term matching (all applied by default)</summary>
        <div className="search-controls__encodings">
          {encodingOptions.map((name) => (
            <label key={name} className="search-controls__checkbox">
              <input type="checkbox" checked={draftEncodings.has(name)} onChange={() => toggle(name)} />
              {name}
            </label>
          ))}
        </div>
      </details>
      <button type="submit">Search dissemination</button>
    </form>
  )
}
