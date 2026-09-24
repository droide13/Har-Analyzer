import { Slider } from 'radix-ui'

interface RangeFieldProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  formatValue?: (value: number) => string
  disabled?: boolean
}

/** Labeled Radix Slider, replacing the unstyled native
 * <input type="range"> fields in Domain Explorer and Identifiers. */
export function RangeField({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  formatValue,
  disabled,
}: RangeFieldProps) {
  return (
    <label className="flex min-w-[200px] flex-1 flex-col gap-2 text-[13px] text-text-muted">
      <span>
        {label} <span className="text-text">{formatValue ? formatValue(value) : value}</span>
      </span>
      <Slider.Root
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={([next]) => onChange(next)}
        disabled={disabled}
        className="relative flex h-4 w-full items-center data-[disabled]:opacity-50"
      >
        <Slider.Track className="relative h-1 grow rounded-full bg-border">
          <Slider.Range className="absolute h-full rounded-full bg-accent" />
        </Slider.Track>
        <Slider.Thumb className="block h-3.5 w-3.5 rounded-full border border-accent bg-bg" />
      </Slider.Root>
    </label>
  )
}
