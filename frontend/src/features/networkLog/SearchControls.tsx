import type { ScopeOptions } from '../../api/types'

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
  pageSize: number
  onPageSizeChange: (size: number) => void
}

/** Direct port of the Streamlit Network Log tab's search panel
 * (tabs/networklog.py::_render_search_controls): same fields, same
 * semantics (filter discards, highlight flags), same default of "all
 * encodings checked". */
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

  function toggleEncoding(name: string) {
    const next = new Set(selectedEncodings)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onEncodingsChange(next)
  }

  return (
    <div className="search-controls">
      <details>
        <summary>Learn How to Search (Negations, Field Filters, etc.)</summary>
        <ul className="search-controls__help">
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
      </details>

      <div className="search-controls__row">
        <label>
          Filter Query (discards entries)
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => onFilterQueryChange(e.target.value)}
            placeholder="e.g. status:4xx -header:image"
          />
        </label>
        <label>
          Highlight Query (highlights matches)
          <input
            type="text"
            value={highlightQuery}
            onChange={(e) => onHighlightQueryChange(e.target.value)}
            placeholder="e.g. cookies:session"
          />
        </label>
      </div>

      <div className="search-controls__row">
        <label>
          Text scope mapping
          <select value={scope} onChange={(e) => onScopeChange(e.target.value)}>
            {Object.entries(scopeOptions).map(([label, value]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <fieldset className="search-controls__methods">
          <legend>Methods target</legend>
          {methodOrder.map((method) => (
            <label key={method} className="search-controls__checkbox">
              <input
                type="checkbox"
                checked={selectedMethods.includes(method)}
                onChange={() => toggleMethod(method)}
              />
              {method}
            </label>
          ))}
        </fieldset>

        <label>
          Results per page
          <input
            type="number"
            min={10}
            max={500}
            step={10}
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
          />
        </label>
      </div>

      <details>
        <summary>Encodings &amp; Hashes for term matching (all applied by default)</summary>
        <div className="search-controls__encodings">
          {encodingOptions.map((name) => (
            <label key={name} className="search-controls__checkbox">
              <input type="checkbox" checked={selectedEncodings.has(name)} onChange={() => toggleEncoding(name)} />
              {name}
            </label>
          ))}
        </div>
      </details>
    </div>
  )
}
