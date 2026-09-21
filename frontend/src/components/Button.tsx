import type { ButtonHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type ButtonSize = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'border border-accent bg-accent text-white hover:brightness-95',
  secondary: 'border border-border bg-bg text-text hover:bg-bg-subtle',
  ghost: 'border border-transparent text-text-muted hover:bg-bg-subtle',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-2.5 py-1 text-[13px]',
  md: 'px-3 py-1.5 text-sm',
}

/** Shared button so "bordered secondary button" stops being redefined
 * per-component -- one place to change padding/radius/hover for all of
 * them, and a primary/ghost variant for the cases that need to stand out
 * or recede rather than every button looking the same regardless of
 * intent. */
export function Button({ variant = 'secondary', size = 'sm', className = '', ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`rounded cursor-pointer disabled:cursor-default disabled:opacity-40 ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...props}
    />
  )
}
