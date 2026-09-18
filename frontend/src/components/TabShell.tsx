import { useState } from 'react'

export interface TabDefinition {
  key: string
  label: string
  render: () => React.ReactNode
}

interface TabShellProps {
  tabs: TabDefinition[]
}

/**
 * Replaces Streamlit's st.tabs. The key architectural difference: Streamlit
 * re-executes and renders every tab's body on every rerun regardless of which
 * one is visible (no lazy/conditional rendering), which was the single
 * biggest source of the original app's lag. Here, only the active tab's
 * `render()` is ever called -- switching tabs costs nothing for the others.
 */
export function TabShell({ tabs }: TabShellProps) {
  const [activeKey, setActiveKey] = useState(tabs[0]?.key)
  const activeTab = tabs.find((t) => t.key === activeKey)

  return (
    <div className="tab-shell">
      <div className="tab-shell__bar" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={tab.key === activeKey}
            className={`tab-shell__tab ${tab.key === activeKey ? 'tab-shell__tab--active' : ''}`}
            onClick={() => setActiveKey(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="tab-shell__panel">{activeTab?.render()}</div>
    </div>
  )
}
