import { useState } from 'react'
import { Popover } from 'radix-ui'

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: string[]
  ariaLabel?: string
  /** Shown in the trigger when value is empty (e.g. nothing picked yet). */
  placeholder?: string
}

/**
 * A native <select>'s open dropdown list is rendered by the browser/OS,
 * not the page -- its width mostly ignores page CSS and is sized from
 * option content, which can render far wider than the closed control (or
 * the whole window) once options are long/unpredictable strings, like a
 * domain or a cookie/query-param key. This renders its own panel instead
 * (via Radix Popover, which owns the positioning/focus-trap/outside-click/
 * Escape chrome), so it's bounded by the same trigger width, with long
 * option text truncated rather than blowing out the layout -- and, since
 * that means no OS-native typeahead either, a plain substring filter input
 * up top so picking one out of a long list (e.g. Dissemination's key
 * picker) doesn't mean scrolling through all of them by hand.
 */
export function Select({ value, onChange, options, ariaLabel, placeholder }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')

  const filteredOptions = options.filter((option) => option.toLowerCase().includes(query.toLowerCase()))

  return (
    <Popover.Root
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open)
        if (!open) setQuery('')
      }}
    >
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label={ariaLabel}
          className="flex w-full items-center justify-between gap-2 rounded border border-border bg-bg px-2 py-1.5 text-left text-text"
        >
          <span className={`overflow-hidden text-ellipsis whitespace-nowrap ${value ? '' : 'text-text-muted'}`}>
            {value || placeholder}
          </span>
          <span className="shrink-0 text-text-muted" aria-hidden="true">
            ▾
          </span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={4}
          className="z-20 w-[var(--radix-popover-trigger-width)] rounded-md border border-border bg-bg p-1 shadow-lg"
        >
          <input
            type="text"
            className="mb-1 w-full rounded border border-border bg-bg px-2 py-1 text-[13px]"
            placeholder="Type to filter..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul className="m-0 max-h-[220px] list-none overflow-y-auto p-0" role="listbox">
            {filteredOptions.map((option) => (
              <li key={option}>
                <button
                  type="button"
                  role="option"
                  aria-selected={option === value}
                  className={`block w-full overflow-hidden truncate rounded px-2 py-1.5 text-left text-[13px] hover:bg-bg-subtle ${
                    option === value ? 'font-semibold text-accent' : 'text-text'
                  }`}
                  onClick={() => {
                    onChange(option)
                    setIsOpen(false)
                  }}
                >
                  {option}
                </button>
              </li>
            ))}
            {filteredOptions.length === 0 && <li className="px-2 py-1.5 text-[13px] text-text-muted">No matches</li>}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
