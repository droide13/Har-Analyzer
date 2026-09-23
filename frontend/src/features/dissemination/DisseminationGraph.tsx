import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { DisseminationFirstSeen, InitiatorChainLink } from '../../api/types'
import { useChartColors } from '../../hooks/useChartColors'
import { buildGraphData, ORANGE, type DomainRow } from './disseminationGraphData'

interface DisseminationGraphProps {
  firstSeen: DisseminationFirstSeen
  initiatorChain: InitiatorChainLink[]
  byDomain: DomainRow[]
  onSelectDomain: (domain: string) => void
}

const LEGEND_ITEMS: { label: string; color: string; dashed?: boolean }[] = [
  { label: 'Initiator (caused/loaded)', color: 'var(--color-text)' },
  { label: 'Cookie', color: ORANGE },
  { label: 'Query param', color: 'var(--color-accent)' },
  { label: 'URL', color: 'var(--color-ok)' },
  { label: 'Other field', color: 'var(--color-text-muted)', dashed: true },
]

/** Node-link graph of a traced value's whole story: the initiator chain
 * that (transitively) caused its first sighting, flowing into the origin,
 * fanning out to every domain it was later seen disseminated to -- arrow
 * style tells you why two domains are connected (see LEGEND_ITEMS). */
export function DisseminationGraph({ firstSeen, initiatorChain, byDomain, onSelectDomain }: DisseminationGraphProps) {
  const colors = useChartColors()

  // Memoized deliberately: DisseminationResults re-renders on every
  // keystroke in the (always-visible, unrelated) narrow/highlight fields
  // below, and on every node click here. Without this, buildGraphData
  // would rerun and hand ECharts a brand-new nodes/edges array each time,
  // which -- since `option` below is passed with notMerge -- would reset
  // the whole force simulation and visibly reshuffle the layout on every
  // one of those interactions, including the very click this graph exists
  // to support.
  //
  // Keyed on a content signature, not the raw props: every narrow/highlight
  // refetch hands back a brand-new byDomain array from the backend even
  // when its contents are unchanged, which would otherwise bust this memo
  // (by reference) on every one of those refetches too.
  const dataSignature = JSON.stringify({ firstSeen, initiatorChain, byDomain })
  const { nodes, edges } = useMemo(
    () => buildGraphData(firstSeen, initiatorChain, byDomain, colors),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dataSignature, colors],
  )

  const option = useMemo(
    () => ({
      tooltip: {
        formatter: (params: { dataType: string; data: { name?: string; tooltip?: string } }) =>
          params.dataType === 'node' ? `<strong>${params.data.name}</strong><br/>${params.data.tooltip ?? ''}` : '',
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: 8,
          // No `gravity` -- it pulls unfixed nodes toward the centroid of
          // the *whole* graph, not toward the origin specifically, which
          // dragged every destination node toward the chain (permanently
          // pinned up and to the left) instead of letting them fan out
          // around the origin. Every destination is already anchored to
          // the origin by its own edge, so gravity isn't needed to keep
          // them from drifting away.
          force: { repulsion: 320, edgeLength: [100, 260] },
          // Edges get a shared opacity here so the (very common) dozens of
          // arrows converging on the origin don't paint over it as a solid
          // blob; each edge's own color/width/dash still applies on top.
          lineStyle: { opacity: 0.55 },
          label: { show: true, color: colors.text, fontSize: 11 },
          emphasis: { focus: 'adjacency' },
          data: nodes,
          links: edges,
        },
      ],
    }),
    [nodes, edges, colors.text],
  )

  const onEvents = useMemo(
    () => ({
      click: (params: { dataType: string; data?: { name?: string } }) => {
        if (params.dataType === 'node' && typeof params.data?.name === 'string') {
          onSelectDomain(params.data.name)
        }
      },
    }),
    [onSelectDomain],
  )

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block rotate-45 text-text" aria-hidden="true">
            ■
          </span>
          The site itself
        </span>
        {LEGEND_ITEMS.map((item) => (
          <span key={item.label} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block w-4"
              style={{ borderTop: `2px ${item.dashed ? 'dashed' : 'solid'} ${item.color}` }}
              aria-hidden="true"
            />
            {item.label}
          </span>
        ))}
      </div>
      <ReactECharts option={option} style={{ height: 520 }} notMerge onEvents={onEvents} />
    </div>
  )
}
