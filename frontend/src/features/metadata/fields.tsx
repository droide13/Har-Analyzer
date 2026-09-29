import { useState } from 'react'
import type { GroundTruthEntry } from '../../api/types'
import { Button } from '../../components/Button'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'

const GROUND_TRUTH_OTHER = 'Other...'

/** One key/value row -- key is a select of the canonical list (kept
 * consistent across files so later cross-referencing ground truth against
 * traffic isn't fighting typos/synonyms) plus an "Other..." escape hatch
 * for anything the list doesn't cover. Value is always free text and never
 * required -- an unfilled row is silently dropped on generate. */
function GroundTruthRow({
  entry,
  keyOptions,
  onChange,
  onRemove,
}: {
  entry: GroundTruthEntry
  keyOptions: string[]
  onChange: (entry: GroundTruthEntry) => void
  onRemove: () => void
}) {
  const [customMode, setCustomMode] = useState(entry.key !== '' && !keyOptions.includes(entry.key))

  return (
    <FormRow>
      <FormField label="Field">
        <select
          className={fieldInputClasses}
          value={customMode ? GROUND_TRUTH_OTHER : entry.key}
          onChange={(e) => {
            if (e.target.value === GROUND_TRUTH_OTHER) {
              setCustomMode(true)
              onChange({ ...entry, key: '' })
            } else {
              setCustomMode(false)
              onChange({ ...entry, key: e.target.value })
            }
          }}
        >
          <option value="" disabled>
            Choose a field...
          </option>
          {keyOptions.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
          <option value={GROUND_TRUTH_OTHER}>{GROUND_TRUTH_OTHER}</option>
        </select>
      </FormField>
      {customMode && (
        <FormField label="Custom field name">
          <input
            type="text"
            className={fieldInputClasses}
            value={entry.key}
            onChange={(e) => onChange({ ...entry, key: e.target.value })}
            placeholder="e.g. Discord handle"
          />
        </FormField>
      )}
      <FormField label="Value">
        <input type="text" className={fieldInputClasses} value={entry.value} onChange={(e) => onChange({ ...entry, value: e.target.value })} />
      </FormField>
      <Button variant="ghost" onClick={onRemove} aria-label="Remove field">
        ✕
      </Button>
    </FormRow>
  )
}

/** Repeatable ground-truth key/value editor -- the real, known values used
 * to set up this capture (an email actually registered with, a name
 * actually entered...), tagged onto the file so a later pass can check
 * where, if anywhere, they leak into the traffic itself. All optional. */
export function GroundTruthEditor({
  entries,
  keyOptions,
  onChange,
}: {
  entries: GroundTruthEntry[]
  keyOptions: string[]
  onChange: (entries: GroundTruthEntry[]) => void
}) {
  return (
    <div>
      {entries.map((entry, i) => (
        <GroundTruthRow
          key={i}
          entry={entry}
          keyOptions={keyOptions}
          onChange={(next) => onChange(entries.map((e, j) => (i === j ? next : e)))}
          onRemove={() => onChange(entries.filter((_, j) => i !== j))}
        />
      ))}
      <Button onClick={() => onChange([...entries, { key: '', value: '' }])}>Add field</Button>
    </div>
  )
}

export function firstKey(labels: Record<string, string>): string {
  return Object.keys(labels)[0] ?? ''
}

interface NamingFieldProps {
  label: string
  /** internal-code -> display-label map from /api/naming/options. */
  options: Record<string, string>
  value: string
  onChange: (value: string) => void
}

/** One of the classification dropdowns -- four of them differ only in which
 * naming-option map they list, so the select markup lives here once. */
export function NamingField({ label, options, value, onChange }: NamingFieldProps) {
  return (
    <FormField label={label}>
      <select className={fieldInputClasses} value={value} onChange={(e) => onChange(e.target.value)}>
        {Object.entries(options).map(([key, optionLabel]) => (
          <option key={key} value={key}>
            {optionLabel}
          </option>
        ))}
      </select>
    </FormField>
  )
}
