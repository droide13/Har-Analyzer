import type { ReactNode } from 'react'
import { CheckboxGroup } from './CheckboxGroup'
import { Disclosure } from './Disclosure'

interface EncodingCheckboxListProps {
  summary: ReactNode
  options: string[]
  selected: Set<string>
  onToggle: (name: string) => void
}

/** Disclosure-wrapped encoding/hash checkbox grid -- Network Log's search
 * controls and Dissemination's search form had byte-identical copies of
 * this. */
export function EncodingCheckboxList({ summary, options, selected, onToggle }: EncodingCheckboxListProps) {
  return (
    <Disclosure summary={summary}>
      <CheckboxGroup layout="grid" options={options} selected={selected} onToggle={onToggle} />
    </Disclosure>
  )
}
