import { useState, type ReactNode } from 'react'
import { Tabs as RadixTabs } from 'radix-ui'

export interface TabDefinition {
  key: string
  label: string
  render: () => ReactNode
}

interface TabsProps {
  tabs: TabDefinition[]
  /** 'page' is the top-level app tab bar; 'panel' is the smaller,
   * bordered-pill bar used inside EntryDetailPanel. */
  variant?: 'page' | 'panel'
  /** Omit both to let Tabs manage its own active-tab state (the 'panel'
   * variant's usage). Passed together, they let a caller (e.g. a "jump to
   * this other tab" action elsewhere on the page) drive which tab is
   * active from outside. */
  activeTab?: string
  onActiveTabChange?: (key: string) => void
}

const ROOT_CLASSES = {
  page: '',
  panel: 'flex min-h-0 flex-1 flex-col',
}

const BAR_CLASSES = {
  page: 'flex gap-1 border-b border-border',
  panel: 'flex flex-wrap gap-1 px-3 pt-2',
}

const TRIGGER_CLASSES = {
  page: 'cursor-pointer border-b-2 border-transparent px-4 py-2 text-sm text-text-muted data-[state=active]:border-accent data-[state=active]:text-text',
  panel:
    'cursor-pointer rounded border border-border px-2 py-1 text-xs text-text-muted data-[state=active]:border-accent data-[state=active]:text-text',
}

const CONTENT_CLASSES = {
  page: 'pt-3',
  // min-h-0 overrides the flex item default of min-height: auto, which
  // would otherwise let a tall child (e.g. a big JSON dump) grow this past
  // its flex-1 share instead of capping it so overflow-auto can scroll.
  panel: 'min-h-0 flex-1 overflow-auto p-3',
}

/**
 * A single Radix Tabs-based component shared by every tab bar in the app.
 * Only the active tab's `render()` is ever called -- Radix Tabs.Content
 * would happily accept every tab's content up front, but only the
 * currently-active one is ever constructed here, so switching tabs costs
 * nothing for the others.
 */
export function Tabs({ tabs, variant = 'page', activeTab: controlledActive, onActiveTabChange }: TabsProps) {
  const [internalActive, setInternalActive] = useState(tabs[0]?.key)
  const active = controlledActive ?? internalActive
  const setActive = onActiveTabChange ?? setInternalActive
  const activeTab = tabs.find((t) => t.key === active)

  return (
    <RadixTabs.Root value={active} onValueChange={setActive} className={ROOT_CLASSES[variant]}>
      <RadixTabs.List className={BAR_CLASSES[variant]}>
        {tabs.map((tab) => (
          <RadixTabs.Trigger key={tab.key} value={tab.key} className={TRIGGER_CLASSES[variant]}>
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {activeTab && (
        <RadixTabs.Content value={activeTab.key} className={CONTENT_CLASSES[variant]}>
          {activeTab.render()}
        </RadixTabs.Content>
      )}
    </RadixTabs.Root>
  )
}
