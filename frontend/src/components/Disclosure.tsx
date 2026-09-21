import { useState, type ReactNode } from 'react'
import { Collapsible } from 'radix-ui'

interface DisclosureProps {
  summary: ReactNode
  children: ReactNode
  defaultOpen?: boolean
  /** Omit both to let Disclosure manage its own open state. Passed
   * together, they let a caller (e.g. a "jump to and expand this one"
   * action elsewhere on the page) drive it from outside. */
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

/** Replaces native <details>/<summary> -- same collapsed-by-default
 * disclosure, but as a component so its trigger/content can be styled
 * consistently across the 5 places that used it. */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
}: DisclosureProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const open = controlledOpen ?? internalOpen
  const setOpen = onOpenChange ?? setInternalOpen

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="text-[13px]">
      <Collapsible.Trigger className="flex cursor-pointer items-center gap-1.5 text-text-muted hover:text-text">
        <span className="inline-block w-3 text-[10px] transition-transform data-[state=open]:rotate-90" data-state={open ? 'open' : 'closed'}>
          ▸
        </span>
        {summary}
      </Collapsible.Trigger>
      <Collapsible.Content className="mt-2 pl-[18px]">{children}</Collapsible.Content>
    </Collapsible.Root>
  )
}
