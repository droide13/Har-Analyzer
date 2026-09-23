import type { ReactNode } from 'react'
import { CheckboxGroup } from './CheckboxGroup'
import { Disclosure } from './Disclosure'

interface EncodingCheckboxListProps {
  summary: ReactNode
  options: string[]
  selected: Set<string>
  /** Hands back the whole next selection rather than the toggled name --
   * both call sites keep this in a Set of state, and each was otherwise
   * repeating the identical clone-then-add-or-delete dance. */
  onChange: (selected: Set<string>) => void
}

/** Disclosure-wrapped encoding/hash checkbox grid -- Network Log's search
 * controls and Dissemination's search form had byte-identical copies of
 * this. */
export function EncodingCheckboxList({ summary, options, selected, onChange }: EncodingCheckboxListProps) {
  function toggle(name: string) {
    const next = new Set(selected)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onChange(next)
  }

  return (
    <Disclosure summary={summary}>
      <CheckboxGroup layout="grid" options={options} selected={selected} onToggle={toggle} />
    </Disclosure>
  )
}
