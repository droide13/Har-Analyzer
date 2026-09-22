import type { DisseminationFirstSeen, InitiatorChainLink } from '../../api/types'
import type { ChartColors } from '../../hooks/useChartColors'

export interface DomainRow {
  Domain: string
  'Entries Hit': number
  'Cookie origin': string
  Fields: string
  'Distinct Values Seen': number
}

export type NodeRole = 'origin' | 'destination' | 'chain' | 'dangling'
export type EdgeType = 'initiator' | 'cookie' | 'query-param' | 'url' | 'other'

export interface GraphNode {
  id: string
  /** Also the domain string -- id/name are always the same value here
   * (there's no separate display-name concept), kept as two fields only
   * because ECharts itself needs both an id (edge source/target
   * references) and a name (the rendered label). */
  name: string
  role: NodeRole
  symbolSize: number
  /** Set only on the site's own domain (the chain's earliest hop, or the
   * origin itself when there's no chain) -- a shape difference rather than
   * another color, since the palette is already spoken for by role/edge
   * colors and a shape reads as "this one's different" regardless of which
   * color it also happens to have. */
  symbol?: 'diamond'
  itemStyle: { color: string; borderColor?: string; borderWidth?: number; borderType?: 'dashed' }
  tooltip: string
  x?: number
  y?: number
  /** Pins the origin and the initiator chain in a fixed straight line (the
   * "spine" of the story) so the physics simulation can't drag them
   * anywhere -- an x/y *seed* alone gets overridden by the force layout
   * once it settles, which is why the initial version of this didn't
   * visibly read as a left-to-right story at all. Destination nodes stay
   * unfixed so they can fan out around the spine via repulsion instead of
   * needing their (possibly hundreds of) positions hand-computed. */
  fixed?: boolean
  /** Per-node label override (merged over the series default) -- used only
   * for the origin, whose label would otherwise render centered on top of
   * its own large fill color (low-contrast, and it's the one node whose
   * name matters most to read clearly). */
  label?: { position: 'bottom'; fontWeight: 'bold' }
}

export interface GraphEdge {
  source: string
  target: string
  edgeType: EdgeType
  lineStyle: { color: string; width: number; type?: 'dashed'; curveness: number }
}

// Badge.tsx's own "orange" tone is a raw hex literal, not a CSS var -- kept
// in sync by hand with that file, which is the source of truth for it.
export const ORANGE = '#d2691e'

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function roleItemStyle(role: NodeRole, colors: ChartColors): GraphNode['itemStyle'] {
  switch (role) {
    case 'origin':
      return { color: colors.accent, borderColor: colors.text, borderWidth: 3 }
    case 'destination':
      return { color: ORANGE }
    case 'dangling':
      return { color: colors.bgSubtle, borderColor: colors.textMuted, borderWidth: 1, borderType: 'dashed' }
    case 'chain':
      return { color: colors.textMuted }
  }
}

function edgeStyleFor(category: Exclude<EdgeType, 'initiator'>, colors: ChartColors, curveness: number): GraphEdge['lineStyle'] {
  switch (category) {
    case 'cookie':
      return { color: ORANGE, width: 2, curveness }
    case 'query-param':
      return { color: colors.accent, width: 2, curveness }
    case 'url':
      return { color: colors.ok, width: 2, curveness }
    case 'other':
      return { color: colors.textMuted, width: 1.5, type: 'dashed', curveness }
  }
}

/** Builds the graph's node/edge data -- kept separate from the component so
 * this assembly/dedup/categorization logic is testable without mounting
 * ECharts. Nodes are deduped by domain (the same domain can legitimately
 * appear at multiple points in the initiator chain, or as both a chain hop
 * and a dissemination destination); destination styling wins over chain
 * styling when a domain plays both roles, since "where the value spread" is
 * the more important signal here. */
export function buildGraphData(
  firstSeen: DisseminationFirstSeen,
  initiatorChain: InitiatorChainLink[],
  byDomain: DomainRow[],
  colors: ChartColors,
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes = new Map<string, GraphNode>()

  function ensureNode(
    domain: string,
    role: NodeRole,
    size: number,
    tooltip: string,
    x?: number,
    y?: number,
    fixed?: boolean,
  ): GraphNode {
    const existing = nodes.get(domain)
    if (existing) {
      if (role === 'destination' && existing.role !== 'origin') {
        existing.role = 'destination'
        existing.itemStyle = roleItemStyle('destination', colors)
        existing.symbolSize = Math.max(existing.symbolSize, size)
        existing.tooltip = tooltip
      }
      return existing
    }
    const node: GraphNode = {
      id: domain,
      name: domain,
      role,
      symbolSize: size,
      itemStyle: roleItemStyle(role, colors),
      tooltip,
      x,
      y,
      fixed,
    }
    nodes.set(domain, node)
    return node
  }

  // Origin goes first (larger, bordered -- see roleItemStyle) so it reads
  // as the hub at a glance, and so it keeps its role even if later touched
  // by a destination/chain check for the same domain. Pinned dead center --
  // the anchor the rest of the "spine" (the chain, below) lines up against.
  const originNode = ensureNode(
    firstSeen.domain,
    'origin',
    40,
    `First seen as a ${firstSeen.origin} at ${firstSeen.when} (${firstSeen.method}) with value ${firstSeen.value}`,
    0,
    0,
    true,
  )
  // Below the node, not centered on it -- a label centered on a large
  // filled circle reads as low-contrast text sitting on top of a solid
  // color, and this is the one node whose name matters most to read.
  originNode.label = { position: 'bottom', fontWeight: 'bold' }

  // Chain-domain sequence, deduped consecutively -- a domain repeating right
  // next to itself (confirmed to happen in real captures) collapses into the
  // same node instead of a meaningless self-loop. x seeding happens in a
  // second pass below, once the final deduped length is known -- the
  // oldest hop needs the most-negative x (furthest left) and the one right
  // before the origin needs the least (closest to 0), which isn't knowable
  // while still walking forward through a chain of unknown final length.
  const chainDomains: string[] = []
  for (const link of initiatorChain) {
    const domain = link.found && link.entry ? link.entry.domain : hostnameOf(link.url)
    const role: NodeRole = link.found ? 'chain' : 'dangling'
    const tooltip =
      link.found && link.entry
        ? `${link.entry.method} ${link.entry.url}`
        : `${link.url} (not captured in this HAR)`
    ensureNode(domain, role, 14, tooltip)
    if (chainDomains[chainDomains.length - 1] !== domain) chainDomains.push(domain)
  }

  // Pinned along a diagonal in chronological order (oldest hop furthest
  // top-left, ending just short of the origin at (0,0)) -- fixed, not just
  // seeded, so this reads as a stable causal line regardless of how the
  // destinations fanning out around it settle. Diagonal rather than a
  // straight horizontal line: a label sitting right on a horizontal wire
  // reads as overlapping/crossed-out text, whereas a line with real slope
  // passes beside each label instead of through it.
  chainDomains.forEach((domain, index) => {
    const node = nodes.get(domain)
    if (node) {
      const distanceFromOrigin = chainDomains.length - index
      node.x = -distanceFromOrigin * 160
      node.y = -distanceFromOrigin * 100
      node.fixed = true
    }
  })

  const edges: GraphEdge[] = []
  // Full-strength text color, not textMuted -- that's meant to be subtle
  // UI chrome, which reads as nearly invisible for a thin line against the
  // chart's own background.
  const initiatorStyle = { color: colors.text, width: 1.5, curveness: 0.1 }
  for (let i = 0; i < chainDomains.length - 1; i++) {
    edges.push({ source: chainDomains[i], target: chainDomains[i + 1], edgeType: 'initiator', lineStyle: initiatorStyle })
  }
  const lastChainDomain = chainDomains[chainDomains.length - 1]
  if (lastChainDomain !== undefined && lastChainDomain !== firstSeen.domain) {
    edges.push({ source: lastChainDomain, target: firstSeen.domain, edgeType: 'initiator', lineStyle: initiatorStyle })
  }

  // The site itself: the chain's earliest hop, or the origin when there's
  // no chain (it was the first-party page load with nothing upstream of
  // it) -- marked with a distinct shape and sized comparably to the origin
  // (not the default 14px chain-node size, which is too small for a
  // rotated square to read as anything but a circle) so it doesn't just
  // blend in as one more small node, even when it also happens to receive
  // the value back later (a common case) and would otherwise just look
  // like an ordinary orange destination.
  const siteNode = nodes.get(chainDomains[0] ?? firstSeen.domain)
  if (siteNode) {
    siteNode.symbol = 'diamond'
    siteNode.symbolSize = Math.max(siteNode.symbolSize, 34)
  }

  // Destinations seeded in a right-facing arc around the origin (angle
  // spread across [-90°, 90°], so x = cos(angle)*radius stays positive --
  // deterministic (same input always seeds the same way, unlike a random
  // scatter) and keeps them visually separate from the chain's line to the
  // left, reinforcing the same left-to-right story.
  let destinationIndex = 0
  const destinationCount = byDomain.filter((row) => row.Domain !== firstSeen.domain).length

  for (const row of byDomain) {
    if (row.Domain === firstSeen.domain) continue

    const size = 12 + Math.min(18, Math.sqrt(row['Entries Hit']) * 3)
    const tooltip = `${row['Entries Hit']} entries hit, ${row['Distinct Values Seen']} distinct value(s) -- ${row.Fields}`
    const angle = destinationCount > 1 ? (destinationIndex / (destinationCount - 1)) * Math.PI - Math.PI / 2 : 0
    const radius = 320
    ensureNode(row.Domain, 'destination', size, tooltip, Math.cos(angle) * radius, Math.sin(angle) * radius)
    destinationIndex += 1

    const fields = row.Fields.split(',')
      .map((f) => f.trim())
      .filter(Boolean)
    const categories = new Set<Exclude<EdgeType, 'initiator'>>()
    for (const field of fields) {
      if (field.includes('Cookie')) categories.add('cookie')
      else if (field === 'Query Params') categories.add('query-param')
      else if (field === 'URL') categories.add('url')
      else categories.add('other')
    }
    if (categories.size === 0) categories.add('other')

    let curveOffset = 0.15
    for (const category of categories) {
      edges.push({
        source: firstSeen.domain,
        target: row.Domain,
        edgeType: category,
        lineStyle: edgeStyleFor(category, colors, curveOffset),
      })
      curveOffset += 0.15
    }
  }

  return { nodes: [...nodes.values()], edges }
}
