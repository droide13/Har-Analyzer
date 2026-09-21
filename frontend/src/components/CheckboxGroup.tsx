import { Checkbox, Label } from 'radix-ui'

interface CheckboxGroupProps {
  legend?: string
  options: string[]
  selected: string[] | Set<string>
  onToggle: (option: string) => void
  /** 'inline' (default) wraps as a flexible row; 'grid' lays out in a
   * fixed 4-column grid -- used by the longer encoding/hash option list. */
  layout?: 'inline' | 'grid'
}

function isSelected(selected: string[] | Set<string>, option: string) {
  return Array.isArray(selected) ? selected.includes(option) : selected.has(option)
}

/** Shared checkbox list -- the method-target fieldset and the encoding/hash
 * option list were two copies of the same label+checkbox markup. */
export function CheckboxGroup({ legend, options, selected, onToggle, layout = 'inline' }: CheckboxGroupProps) {
  return (
    <fieldset
      className={`m-0 border-0 p-0 ${
        layout === 'grid' ? 'grid grid-cols-4 gap-x-4 gap-y-1' : 'flex flex-wrap items-center gap-2'
      }`}
    >
      {legend && <legend className="mb-1 w-full p-0 text-[13px] text-text-muted">{legend}</legend>}
      {options.map((option) => (
        <Label.Root key={option} className="inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap">
          <Checkbox.Root
            checked={isSelected(selected, option)}
            onCheckedChange={() => onToggle(option)}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-border bg-bg data-[state=checked]:border-accent data-[state=checked]:bg-accent"
          >
            <Checkbox.Indicator className="text-[10px] text-white">✓</Checkbox.Indicator>
          </Checkbox.Root>
          {option}
        </Label.Root>
      ))}
    </fieldset>
  )
}
