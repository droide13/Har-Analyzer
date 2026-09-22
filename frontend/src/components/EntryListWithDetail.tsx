import { Group, Panel, Separator } from 'react-resizable-panels'
import type { EntrySummary } from '../api/types'
import { EntryDetailPanel, type ExtraDetailTab } from './EntryDetailPanel'
import { EntryListTable } from './EntryListTable'

interface EntryListWithDetailProps {
  uploadId: string
  items: EntrySummary[]
  selectedIndex: number | null
  onSelectRow: (index: number) => void
  onClose: () => void
  showMatchedFields?: boolean
  emptyMessage?: string
  extraTabs?: ExtraDetailTab[]
}

/**
 * One list + its own resizable detail panel. Used per-table (Network Log;
 * Dissemination's Initiator Traced Entries and Matching HAR Entries each
 * get their own instance) rather than one shared panel for multiple lists --
 * that shared-panel approach fought react-resizable-panels' height model at
 * every turn (forced height, sticky positioning, scroll anchoring) for a
 * layout nobody actually wanted: two differently-sized lists jammed into one
 * slider. Each instance here is sized to its own list, independently.
 */
export function EntryListWithDetail({
  uploadId,
  items,
  selectedIndex,
  onSelectRow,
  onClose,
  showMatchedFields,
  emptyMessage,
  extraTabs,
}: EntryListWithDetailProps) {
  const table = (
    <EntryListTable
      items={items}
      selectedIndex={selectedIndex}
      onSelectRow={onSelectRow}
      showMatchedFields={showMatchedFields}
      emptyMessage={emptyMessage}
    />
  )

  if (selectedIndex === null) {
    return table
  }

  return (
    <Group orientation="horizontal" style={{ height: '70vh' }}>
      <Panel minSize="30%" className="pr-3">
        {table}
      </Panel>
      <Separator className="w-1.5 shrink-0 cursor-col-resize rounded-full bg-border transition-colors hover:bg-accent active:bg-accent" />
      <Panel defaultSize={420} minSize={320} maxSize={800}>
        <EntryDetailPanel uploadId={uploadId} index={selectedIndex} onClose={onClose} extraTabs={extraTabs} />
      </Panel>
    </Group>
  )
}
