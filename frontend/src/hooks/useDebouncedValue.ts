import { useEffect, useState } from 'react'

/**
 * Debounces a fast-changing value (e.g. a search box) before it drives a
 * network request. The original Streamlit app re-filtered locally on every
 * keystroke with no round trip; here each change is an HTTP call, so this
 * is what keeps typing responsive instead of firing a request per key.
 */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
