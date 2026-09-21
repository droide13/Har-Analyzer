import type { ReactNode } from 'react'

/** Shared classes for native text/number/date/select/textarea controls --
 * applied directly on those elements (no wrapper component needed, native
 * semantics are already correct), so every form control across the app
 * gets the same border/padding/radius from one place. */
export const fieldInputClasses = 'rounded border border-border bg-bg px-2 py-1.5 text-text'

export function FormRow({ children }: { children: ReactNode }) {
  return <div className="mb-3 flex flex-wrap items-end gap-4">{children}</div>
}

interface FormFieldProps {
  label: ReactNode
  hint?: ReactNode
  children: ReactNode
}

/** Label + control + optional hint, replacing the `search-controls__row`
 * label wrapper that was hand-repeated across every filter form in the
 * app. */
export function FormField({ label, hint, children }: FormFieldProps) {
  return (
    <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-[13px] text-text-muted">
      {label}
      {children}
      {hint && <span className="text-xs">{hint}</span>}
    </label>
  )
}
