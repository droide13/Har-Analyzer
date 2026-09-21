import { ToggleGroup } from 'radix-ui'

interface SegmentedControlOption {
  value: string
  label: string
}

interface SegmentedControlProps {
  legend?: string
  options: SegmentedControlOption[]
  value: string
  onChange: (value: string) => void
}

/** Exclusive pill toggle, replacing the radio-fieldset markup that
 * AggregateToggleView and DomainExplorer each hand-rolled for their own
 * "pick one of a few views" control. */
export function SegmentedControl({ legend, options, value, onChange }: SegmentedControlProps) {
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2">
      {legend && <span className="text-[13px] text-text-muted">{legend}</span>}
      <ToggleGroup.Root
        type="single"
        value={value}
        onValueChange={(next) => {
          if (next) onChange(next)
        }}
        className="inline-flex overflow-hidden rounded border border-border"
      >
        {options.map((option) => (
          <ToggleGroup.Item
            key={option.value}
            value={option.value}
            className="cursor-pointer border-l border-border px-2.5 py-1 text-[13px] first:border-l-0 data-[state=on]:bg-accent data-[state=on]:text-white"
          >
            {option.label}
          </ToggleGroup.Item>
        ))}
      </ToggleGroup.Root>
    </div>
  )
}
