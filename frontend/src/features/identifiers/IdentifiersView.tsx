import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIdentifiers } from '../../api/identifiers'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { IdentifiersSection } from './IdentifiersSection'

interface IdentifiersViewProps {
  uploadId: string
}

const SORT_OPTIONS = ['Appearances', 'Entropy', 'Avg length', 'Unique values'] as const

/** Direct port of tabs/identifiers/identifiers_ui.py: 4 threshold sliders +
 * a name search + noise-key exclusion, applied server-side (the same
 * extract/filter/sort pipeline as the original), rendered as two sections. */
export function IdentifiersView({ uploadId }: IdentifiersViewProps) {
  const [nameQuery, setNameQuery] = useState('')
  const debouncedNameQuery = useDebouncedValue(nameQuery)
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]>('Appearances')
  const [excludeCommon, setExcludeCommon] = useState(true)
  const [minAppearances, setMinAppearances] = useState(20)
  const debouncedMinAppearances = useDebouncedValue(minAppearances)
  const [maxUniqueValues, setMaxUniqueValues] = useState(5)
  const debouncedMaxUniqueValues = useDebouncedValue(maxUniqueValues)
  const [minAvgLength, setMinAvgLength] = useState(20)
  const debouncedMinAvgLength = useDebouncedValue(minAvgLength)
  const [minAvgEntropy, setMinAvgEntropy] = useState(2.5)
  const debouncedMinAvgEntropy = useDebouncedValue(minAvgEntropy)

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      'identifiers',
      uploadId,
      debouncedNameQuery,
      sortBy,
      excludeCommon,
      debouncedMinAppearances,
      debouncedMaxUniqueValues,
      debouncedMinAvgLength,
      debouncedMinAvgEntropy,
    ],
    queryFn: () =>
      fetchIdentifiers(uploadId, {
        min_appearances: debouncedMinAppearances,
        max_unique_values: debouncedMaxUniqueValues,
        min_avg_length: debouncedMinAvgLength,
        min_avg_entropy: debouncedMinAvgEntropy,
        name_query: debouncedNameQuery,
        exclude_common: excludeCommon,
        sort_by: sortBy,
      }),
    placeholderData: (previous) => previous,
  })

  return (
    <div className="identifiers">
      <h3>Stable Identifier Detection</h3>
      <p className="caption">
        Flags query params and cookies that appear often, take on few distinct values, and look sufficiently
        random/long to be a session, tracking, or auth token -- rather than an ordinary low-cardinality param like{' '}
        <code>sort</code> or <code>lang</code>.
      </p>

      <details>
        <summary>Common noise keys</summary>
        <p className="caption">
          page, limit, offset, sort, order, q, query, lang, locale, cache, v, version, format, type, action,
          utm_source, utm_medium, utm_campaign, utm_term, utm_content
        </p>
      </details>

      <div className="search-controls__row">
        <label>
          Search key name
          <input
            type="text"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            placeholder="e.g. sess, token, sid"
          />
        </label>
        <label>
          Sort by
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as (typeof SORT_OPTIONS)[number])}>
            {SORT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="search-controls__checkbox">
          <input type="checkbox" checked={excludeCommon} onChange={(e) => setExcludeCommon(e.target.checked)} />
          Exclude common noise keys
        </label>
      </div>

      <div className="search-controls__row">
        <label>
          Minimum appearances ({minAppearances})
          <input
            type="range"
            min={1}
            max={200}
            value={minAppearances}
            onChange={(e) => setMinAppearances(Number(e.target.value))}
          />
        </label>
        <label>
          Max unique values ({maxUniqueValues})
          <input
            type="range"
            min={1}
            max={20}
            value={maxUniqueValues}
            onChange={(e) => setMaxUniqueValues(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="search-controls__row">
        <label>
          Minimum avg value length ({minAvgLength})
          <input
            type="range"
            min={0}
            max={64}
            value={minAvgLength}
            onChange={(e) => setMinAvgLength(Number(e.target.value))}
          />
        </label>
        <label>
          Minimum avg entropy ({minAvgEntropy.toFixed(1)} bits/char)
          <input
            type="range"
            min={0}
            max={6}
            step={0.1}
            value={minAvgEntropy}
            onChange={(e) => setMinAvgEntropy(Number(e.target.value))}
          />
        </label>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="error-text">Failed to load identifiers.</p>}

      {data && (
        <>
          <IdentifiersSection label="Query Parameters" identifiers={data.query_params} />
          <hr />
          <p className="caption">
            First Seen As marks where a cookie turned up first: a Response Cookie was issued during this capture, a
            Request Cookie already existed.
          </p>
          <IdentifiersSection label="Cookies" identifiers={data.cookies} />
        </>
      )}
    </div>
  )
}
