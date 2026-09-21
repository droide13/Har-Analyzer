import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIdentifiers } from '../../api/identifiers'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { Disclosure } from '../../components/Disclosure'
import { FormField, FormRow, fieldInputClasses } from '../../components/FormField'
import { ErrorState, LoadingState } from '../../components/QueryState'
import { RangeField } from '../../components/RangeField'
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
    <div>
      <h3 className="text-base font-semibold">Stable Identifier Detection</h3>
      <p className="my-1 mb-3 text-[13px] text-text-muted">
        Flags query params and cookies that appear often, take on few distinct values, and look sufficiently
        random/long to be a session, tracking, or auth token -- rather than an ordinary low-cardinality param like{' '}
        <code>sort</code> or <code>lang</code>.
      </p>

      <Disclosure summary="Common noise keys">
        <p className="text-[13px] text-text-muted">
          page, limit, offset, sort, order, q, query, lang, locale, cache, v, version, format, type, action,
          utm_source, utm_medium, utm_campaign, utm_term, utm_content
        </p>
      </Disclosure>

      <FormRow>
        <FormField label="Search key name">
          <input
            type="text"
            className={fieldInputClasses}
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            placeholder="e.g. sess, token, sid"
          />
        </FormField>
        <FormField label="Sort by">
          <select
            className={fieldInputClasses}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as (typeof SORT_OPTIONS)[number])}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </FormField>
        <label className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
          <input type="checkbox" checked={excludeCommon} onChange={(e) => setExcludeCommon(e.target.checked)} />
          Exclude common noise keys
        </label>
      </FormRow>

      <FormRow>
        <RangeField label="Minimum appearances" value={minAppearances} min={1} max={200} onChange={setMinAppearances} />
        <RangeField label="Max unique values" value={maxUniqueValues} min={1} max={20} onChange={setMaxUniqueValues} />
      </FormRow>

      <FormRow>
        <RangeField label="Minimum avg value length" value={minAvgLength} min={0} max={64} onChange={setMinAvgLength} />
        <RangeField
          label="Minimum avg entropy"
          value={minAvgEntropy}
          min={0}
          max={6}
          step={0.1}
          onChange={setMinAvgEntropy}
          formatValue={(v) => `${v.toFixed(1)} bits/char`}
        />
      </FormRow>

      {isLoading && <LoadingState />}
      {isError && <ErrorState label="Failed to load identifiers." />}

      {data && (
        <>
          <IdentifiersSection label="Query Parameters" identifiers={data.query_params} />
          <hr className="my-3 border-border" />
          <p className="my-1 mb-3 text-[13px] text-text-muted">
            First Seen As marks where a cookie turned up first: a Response Cookie was issued during this capture, a
            Request Cookie already existed.
          </p>
          <IdentifiersSection label="Cookies" identifiers={data.cookies} />
        </>
      )}
    </div>
  )
}
