import { useEffect, useState } from 'react'
import { Checkbox, Label } from 'radix-ui'
import type { GroundTruthEntry } from '../api/types'
import { Button } from './Button'
import { Disclosure } from './Disclosure'

interface GroundTruthCheckboxListProps {
  entries: GroundTruthEntry[]
  includedKeys: Set<string>
  onToggle: (key: string) => void
}

/** Ground truth's key/value pairs need their own value shown alongside each
 * checkbox, unlike the flat option lists CheckboxGroup handles. */
function GroundTruthCheckboxList({ entries, includedKeys, onToggle }: GroundTruthCheckboxListProps) {
  return (
    <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
      {entries.map((g) => (
        <Label.Root key={g.key} className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
          <Checkbox.Root
            checked={includedKeys.has(g.key)}
            onCheckedChange={() => onToggle(g.key)}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-border bg-bg data-[state=checked]:border-accent data-[state=checked]:bg-accent"
          >
            <Checkbox.Indicator className="text-[10px] text-white">✓</Checkbox.Indicator>
          </Checkbox.Root>
          <span className="font-semibold">{g.key}:</span>
          <span className="font-mono text-text-muted">{g.value}</span>
        </Label.Root>
      ))}
    </fieldset>
  )
}

interface GroundTruthSearchControlProps {
  /** This file's own tagged values (Metadata tab). Nothing renders when empty. */
  groundTruth: GroundTruthEntry[]
  /** The keys the last "Search" click submitted; null = no search run yet.
   * Only used here to tell whether a search is currently active -- the
   * checkbox draft below is independent local state. */
  active: Set<string> | null
  /** Fired with the checked keys when "Search" is clicked. */
  onSearch: (keys: Set<string>) => void
}

/** Search this file's ground truth values against the entries below --
 * shared by Network Log and Dissemination so both offer identical
 * ground-truth search behavior instead of two hand-rolled copies drifting
 * apart. Checkboxes are all checked by default and visible right away;
 * checking/unchecking one is free (no request), and the full scan itself
 * -- real work, every entry x every value x every encoding -- only runs
 * when "Search" is clicked. */
export function GroundTruthSearchControl({ groundTruth, active, onSearch }: GroundTruthSearchControlProps) {
  const keySignature = groundTruth.map((g) => g.key).join('␟')
  const [selected, setSelected] = useState<Set<string>>(() => new Set(groundTruth.map((g) => g.key)))

  // Re-derives the all-checked default whenever the tagged key *list*
  // changes (not on every groundTruth object identity change) -- covers
  // the common case of this component mounting before the ground-truth
  // fetch resolves, plus a value being added/removed in the Metadata tab
  // while this tab stays mounted.
  useEffect(() => {
    setSelected(new Set(groundTruth.map((g) => g.key)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keySignature])

  if (groundTruth.length === 0) return null

  function toggle(key: string) {
    const next = new Set(selected)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    setSelected(next)
  }

  return (
    <Disclosure summary="Ground truth" defaultOpen>
      <div className="flex flex-col items-start gap-2">
        <GroundTruthCheckboxList entries={groundTruth} includedKeys={selected} onToggle={toggle} />
        <Button onClick={() => onSearch(selected)} disabled={selected.size === 0}>
          {active === null ? 'Search ground truth values' : 'Search again'}
        </Button>
      </div>
    </Disclosure>
  )
}
