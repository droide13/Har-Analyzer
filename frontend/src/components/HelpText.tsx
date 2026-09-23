import type { ReactNode } from 'react'

/** The explanatory paragraph under a heading/control that nearly every view
 * has -- same size, tone and spacing in all of them, so the class string
 * stops being retyped (and drifting) per view. */
export function HelpText({ children }: { children: ReactNode }) {
  return <p className="my-1 mb-3 text-[13px] text-text-muted">{children}</p>
}
