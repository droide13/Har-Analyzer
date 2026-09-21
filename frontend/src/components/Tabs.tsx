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
  panel: 'flex-1 overflow-auto p-3',
}

/**
 * Replaces TabShell (and EntryDetailPanel's own parallel hand-rolled tab
 * bar) with a single Radix Tabs-based component. Only the active tab's
 * `render()` is ever called -- Radix Tabs.Content would happily accept
 * every tab's content up front, but only the currently-active one is ever
 * constructed here, preserving the "switching tabs costs nothing for the
 * others" behavior this app was rewritten from Streamlit to get.
 */
export function Tabs({ tabs, variant = 'page' }: TabsProps) {
  const [active, setActive] = useState(tabs[0]?.key)
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
