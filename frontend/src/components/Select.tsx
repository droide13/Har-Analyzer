import { useEffect, useRef, useState } from 'react'

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: string[]
  ariaLabel?: string
}

/**
 * A native <select>'s open dropdown list is rendered by the browser/OS,
 * not the page -- its width mostly ignores page CSS and is sized from
 * option content, which can render far wider than the closed control (or
 * the whole window) once options are long/unpredictable strings, like a
 * domain or a cookie/query-param key. This renders its own panel instead,
 * so it's bounded by the same container width as the closed control, with
 * long option text truncated rather than blowing out the layout -- and,
 * since that means no OS-native typeahead either, a plain substring filter
 * input up top so picking one out of a long list (e.g. Dissemination's key
 * picker) doesn't mean scrolling through all of them by hand.
 */
export function Select({ value, onChange, options, ariaLabel }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (isOpen) searchRef.current?.focus()
    else setQuery('')
  }, [isOpen])

  const filteredOptions = options.filter((option) => option.toLowerCase().includes(query.toLowerCase()))

  return (
    <div className="dropdown" ref={rootRef}>
      <button
        type="button"
        className="dropdown__trigger"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="dropdown__value">{value}</span>
        <span className="dropdown__chevron" aria-hidden="true">
          ▾
        </span>
      </button>
      {isOpen && (
        <div className="dropdown__panel">
          <input
            ref={searchRef}
            type="text"
            className="dropdown__search"
            placeholder="Type to filter..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul className="dropdown__list" role="listbox">
            {filteredOptions.map((option) => (
              <li key={option}>
                <button
                  type="button"
                  role="option"
                  aria-selected={option === value}
                  className={`dropdown__option ${option === value ? 'dropdown__option--selected' : ''}`}
                  onClick={() => {
                    onChange(option)
                    setIsOpen(false)
                  }}
                >
                  {option}
                </button>
              </li>
            ))}
            {filteredOptions.length === 0 && <li className="dropdown__empty">No matches</li>}
          </ul>
        </div>
      )}
    </div>
  )
}
