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
  const selectedBadges = items.find((item) => item.index === selectedIndex)?.badges

  // The table's own Panel is rendered unconditionally -- only the detail
  // Panel + Separator come and go -- so opening the detail panel for the
  // first time never changes the table's position in the tree. It used to
  // be selectedIndex === null ? table : <Group><Panel>{table}</Panel>...,
  // which switches the table's parent from nothing to a Group/Panel on the
  // very first selection; React can't tell that's "the same table" across
  // such a different ancestor chain, so it remounted EntryListTable/
  // DataTable from scratch -- fresh containerRef, fresh virtualizer, and
  // the scroll position you had reset to 0. Keeping the table's Panel
  // always mounted keeps the table itself always mounted, so its scroll
  // position survives selecting a row for the first time.
  return (
    <Group orientation="horizontal" style={{ height: selectedIndex === null ? undefined : '70vh' }}>
      <Panel minSize="30%" className={selectedIndex === null ? '' : 'pr-3'}>
        <EntryListTable
          items={items}
          selectedIndex={selectedIndex}
          onSelectRow={onSelectRow}
          showMatchedFields={showMatchedFields}
          emptyMessage={emptyMessage}
        />
      </Panel>
      {selectedIndex !== null && (
        <>
          <Separator className="w-1.5 shrink-0 cursor-col-resize rounded-full bg-border transition-colors hover:bg-accent active:bg-accent" />
          <Panel defaultSize={420} minSize={320} maxSize={800}>
            <EntryDetailPanel uploadId={uploadId} index={selectedIndex} onClose={onClose} extraTabs={extraTabs} badges={selectedBadges} />
          </Panel>
        </>
      )}
    </Group>
  )
}
