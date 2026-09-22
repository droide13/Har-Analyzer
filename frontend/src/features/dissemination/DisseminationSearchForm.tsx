import { useEffect, useState } from 'react'
import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { EncodingCheckboxList } from '../../components/EncodingCheckboxList'

interface DisseminationSearchFormProps {
  encodingOptions: string[]
  onSearch: (encodings: string[]) => void
  /** A search has already run for the current key -- e.g. auto-triggered by
   * the Identifiers tab's "Trace" button, which calls onSearch directly
   * without this form ever being submitted. Shows a status badge next to
   * the button so that isn't invisible. */
  hasSearched?: boolean
}

/**
 * Encoding checkboxes + explicit submit, mirroring the original's
 * st.form: ticking/unticking a box costs nothing here (no query fires)
 * until "Search dissemination" is clicked -- unlike Network Log's
 * always-live filter controls.
 */
export function DisseminationSearchForm({ encodingOptions, onSearch, hasSearched = false }: DisseminationSearchFormProps) {
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
      className="mb-3 flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch([...draftEncodings])
      }}
    >
      <p className="my-1 text-[13px] text-text-muted">
        This scans every field of every entry and is not run automatically. Untick any encoded/hashed forms you
        don't want, then click Search.
      </p>
      <EncodingCheckboxList
        summary="Encodings & Hashes for term matching (all applied by default)"
        options={encodingOptions}
        selected={draftEncodings}
        onToggle={toggle}
      />
      <div className="flex items-center gap-2">
        <Button type="submit" variant="primary" className="w-fit">
          Search dissemination
        </Button>
        {hasSearched && <Badge tone="ok">✓ Results below</Badge>}
      </div>
    </form>
  )
}
