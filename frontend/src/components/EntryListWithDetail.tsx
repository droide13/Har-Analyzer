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
 * Shared by Network Log and Dissemination: the entry list, and -- once a row
 * is selected -- a resizable detail panel alongside it, via react-resizable-
 * panels rather than a hand-rolled width (a fixed 420px column made the
 * table narrower than the browser could redistribute cleanly, breaking its
 * header layout; letting a maintained library own the split avoids that).
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
    <Group orientation="horizontal" className="h-[70vh]">
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
