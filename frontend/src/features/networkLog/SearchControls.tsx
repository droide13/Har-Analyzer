import type { GroundTruthEntry, ScopeOptions } from '../../api/types'
import { CheckboxGroup } from '../../components/CheckboxGroup'
import { Disclosure } from '../../components/Disclosure'
import { EncodingCheckboxList } from '../../components/EncodingCheckboxList'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { GroundTruthSearchControl } from '../../components/GroundTruthSearchControl'

interface SearchControlsProps {
  filterQuery: string
  onFilterQueryChange: (value: string) => void
  highlightQuery: string
  onHighlightQueryChange: (value: string) => void
  scope: string
  onScopeChange: (value: string) => void
  scopeOptions: ScopeOptions
  methodOrder: string[]
  selectedMethods: string[]
  onMethodsChange: (methods: string[]) => void
  encodingOptions: string[]
  selectedEncodings: Set<string>
  onEncodingsChange: (encodings: Set<string>) => void
  /** This file's own tagged ground-truth values (Metadata tab) -- empty
   * when none have been tagged, in which case the section doesn't render. */
  groundTruth: GroundTruthEntry[]
  groundTruthKeys: Set<string> | null
  onSearchGroundTruth: (keys: Set<string>) => void
  pageSize: number
  onPageSizeChange: (size: number) => void
}

/** Network Log's search panel: a filter query (discards non-matching
 * entries), an independent highlight query (flags matches without
 * discarding), and the shared scope/method/encoding controls both use --
 * defaults to every encoding checked. */
export function SearchControls({
  filterQuery,
  onFilterQueryChange,
  highlightQuery,
  onHighlightQueryChange,
  scope,
  onScopeChange,
  scopeOptions,
  methodOrder,
  selectedMethods,
  onMethodsChange,
  encodingOptions,
  selectedEncodings,
  onEncodingsChange,
  groundTruth,
  groundTruthKeys,
  onSearchGroundTruth,
  pageSize,
  onPageSizeChange,
}: SearchControlsProps) {
  function toggleMethod(method: string) {
    onMethodsChange(
      selectedMethods.includes(method)
        ? selectedMethods.filter((m) => m !== method)
        : [...selectedMethods, method],
    )
  }

  return (
    <div className="mb-3 flex flex-col gap-3 rounded-md border border-border bg-bg-subtle p-3">
      <Disclosure summary="Learn How to Search (Negations, Field Filters, etc.)">
        <ul className="text-[13px] text-text-muted">
          <li>
            <strong>Free Text:</strong> searches the selected field scope, e.g. <code>api/v1</code>.
          </li>
          <li>
            <strong>Negation (-):</strong> exclude items, e.g. <code>-status:200</code> or <code>-google</code>.
          </li>
          <li>
            <strong>Field prefixes:</strong> <code>url:</code>, <code>cookies:</code>, <code>status:4xx</code>,{' '}
            <code>method:</code>, <code>header:</code>, <code>body:</code>.
          </li>
        </ul>
      </Disclosure>

      <FormRow>
        <FormField label="Filter Query (discards entries)">
          <input
            type="text"
            className={fieldInputClasses}
            value={filterQuery}
            onChange={(e) => onFilterQueryChange(e.target.value)}
            placeholder="e.g. status:4xx -header:image"
          />
        </FormField>
        <FormField label="Highlight Query (highlights matches)">
          <input
            type="text"
            className={fieldInputClasses}
            value={highlightQuery}
            onChange={(e) => onHighlightQueryChange(e.target.value)}
            placeholder="e.g. cookies:session"
          />
        </FormField>
      </FormRow>

      <FormRow>
        <FormField label="Text scope mapping">
          <select className={fieldInputClasses} value={scope} onChange={(e) => onScopeChange(e.target.value)}>
            {Object.entries(scopeOptions).map(([label, value]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FormField>

        <CheckboxGroup legend="Methods target" options={methodOrder} selected={selectedMethods} onToggle={toggleMethod} />

        <FormField label="Results per page">
          <input
            type="number"
            className={fieldInputClasses}
            min={10}
            max={500}
            step={10}
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
          />
        </FormField>
      </FormRow>

      <EncodingCheckboxList
        summary="Encodings & Hashes for term matching (all applied by default)"
        options={encodingOptions}
        selected={selectedEncodings}
        onChange={onEncodingsChange}
      />

      <GroundTruthSearchControl groundTruth={groundTruth} active={groundTruthKeys} onSearch={onSearchGroundTruth} />
    </div>
  )
}
