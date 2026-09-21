import type { ReactNode } from 'react'

export type BadgeTone = 'ok' | 'error' | 'muted' | 'neutral' | 'orange'

const TONE_CLASSES: Record<BadgeTone, string> = {
  ok: 'bg-ok/15 text-ok',
  error: 'bg-error/15 text-error',
  muted: 'bg-bg-subtle text-text-muted',
  neutral: 'bg-accent/15 text-accent',
  orange: 'bg-[rgba(255,140,0,0.15)] text-[#d2691e]',
}

interface BadgeProps {
  tone: BadgeTone
  children: ReactNode
}

/** Small tinted pill for a status/method/tag value that needs to stay
 * legible at a glance across dozens of table rows -- one shared shape and
 * tone set instead of ad-hoc colored text per view. */
export function Badge({ tone, children }: BadgeProps) {
  return (
    <span
      className={`mr-1 mb-0.5 inline-block rounded-sm px-1.5 py-0.5 font-mono text-[11px] leading-none ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  )
}
