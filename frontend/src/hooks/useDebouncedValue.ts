import { useEffect, useState } from 'react'

/**
 * Debounces a fast-changing value (e.g. a search box) before it drives a
 * network request -- keeps typing responsive instead of firing a request
 * per keystroke.
 */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
