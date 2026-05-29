import Dagre from "@dagrejs/dagre"

import type { StageName } from "@/types/query"

import type {
  BuilderSnapshot,
  CanvasEdge,
  CanvasEdgeVariant,
  CanvasNode,
  CycleStep,
  NextPlaceholder,
  ResearchStage,
} from "./types"

const NODE_WIDTH = 288
const RESEARCH_WIDTH = 448
const SLOT_WIDTH = 176
const RESEARCH_HEIGHT = 260
const DEFAULT_HEIGHT = 120
const PLACEHOLDER_HEIGHT = 90
const SLOT_HEIGHT = 64
const RANKSEP = 140
const NODESEP = 80

const STAGE_ORDER: StageName[] = [
  "extract",
  "expand",
  "retrieve",
  "cluster",
  "persona",
]
const STAGE_LABEL: Record<StageName, string> = {
  extract: "Extract focal claim",
  expand: "Expand query",
  retrieve: "Retrieve references",
  cluster: "Compute clusters",
  persona: "Generate persona pool",
}
const STAGE_DESCRIPTION: Record<StageName, string> = {
  extract: "Extracting and decomposing research problem...",
  expand: "Expanding query with related terms...",
  retrieve: "Retrieving supporting papers from Semantic Scholar...",
  cluster: "Clustering papers by theme...",
  persona: "Building researcher personas from clusters...",
}

export const idFor = {
  research: () => "research" as const,
  claim: () => "claim" as const,
  agent: (slot: 1 | 2 | 3) => `agent-${slot}` as const,
  agentSlot: (slot: 1 | 2 | 3) => `agent-slot-${slot}` as const,
  steer: (n: number) => `s${n}` as const,
  debate: (n: number) => `d${n}` as const,
  placeholder: () => "placeholder" as const,
}

type ChainSnapshot = {
  cycles: CycleStep[]
  nextPlaceholder: NextPlaceholder | null
  blockedReason: string | null
}

const ORIGIN = { x: 0, y: 0 } as const

function deriveResearchStages(
  pipelineStages: BuilderSnapshot["pipelineStages"],
): ResearchStage[] | undefined {
  const stages: ResearchStage[] = STAGE_ORDER.map((stage) => {
    const base = {
      key: stage,
      name: STAGE_LABEL[stage],
      description: STAGE_DESCRIPTION[stage],
    }
    const status = pipelineStages[stage]
    if (status === "complete") return { ...base, status: "done" }
    if (status === "running") return { ...base, status: "running" }
    return { ...base, status: "pending" }
  })
  const anyActive = stages.some((s) => s.status !== "pending")
  return anyActive ? stages : undefined
}

function agentTargetForSlot(
  builder: Pick<BuilderSnapshot, "team">,
  slot: 1 | 2 | 3,
): { id: string; isReal: boolean } {
  const real = builder.team[slot - 1]
  return real
    ? { id: idFor.agent(slot), isReal: true }
    : { id: idFor.agentSlot(slot), isReal: false }
}

export function deriveNodes(
  chain: ChainSnapshot,
  builder: BuilderSnapshot,
): CanvasNode[] {
  const nodes: CanvasNode[] = []

  nodes.push({
    id: idFor.research(),
    type: "research",
    position: { ...ORIGIN },
    data: {
      kind: "research",
      query: builder.query,
      stages: deriveResearchStages(builder.pipelineStages),
    },
  })

  if (builder.focalClaim != null) {
    nodes.push({
      id: idFor.claim(),
      type: "claim",
      position: { ...ORIGIN },
      data: { kind: "claim", focalClaim: builder.focalClaim },
    })
  }

  if (builder.focalClaim != null) {
    for (let s = 1; s <= 3; s++) {
      const slot = s as 1 | 2 | 3
      const member = builder.team[slot - 1]
      if (member) {
        nodes.push({
          id: idFor.agent(slot),
          type: "agent",
          position: { ...ORIGIN },
          data: {
            kind: "agent",
            clusterId: member.cluster_id,
            name: member.name,
            reasoningStyle: member.reasoning_style,
            slot,
            persona: member,
          },
        })
      } else {
        nodes.push({
          id: idFor.agentSlot(slot),
          type: "placeholder",
          position: { ...ORIGIN },
          data: {
            kind: "placeholder",
            nextKind: "agent-slot",
            n: 0,
            slot,
            disabled: true,
            blockedReason: "Pick from the researcher pool",
          },
        })
      }
    }
  }

  chain.cycles.forEach((step) => {
    nodes.push({
      id: step.id,
      type: step.kind,
      position: { ...ORIGIN },
      data: { kind: step.kind, n: step.n, status: step.status },
    })
  })

  if (chain.nextPlaceholder) {
    nodes.push({
      id: idFor.placeholder(),
      type: "placeholder",
      position: { ...ORIGIN },
      data: {
        kind: "placeholder",
        nextKind: chain.nextPlaceholder.kind,
        n: chain.nextPlaceholder.n,
        disabled: chain.blockedReason != null,
        blockedReason: chain.blockedReason,
      },
    })
  }

  return nodes
}

export function deriveEdges(
  chain: Pick<ChainSnapshot, "cycles" | "nextPlaceholder">,
  builder: Pick<BuilderSnapshot, "focalClaim" | "team">,
): CanvasEdge[] {
  const edges: CanvasEdge[] = []
  const teamCount = Math.min(builder.team.length, 3)

  if (builder.focalClaim != null) {
    edges.push({
      id: "e:research-claim",
      source: idFor.research(),
      target: idFor.claim(),
      type: "chain",
      data: { variant: "animated" },
    })
  }

  if (builder.focalClaim != null) {
    for (let s = 1; s <= 3; s++) {
      const slot = s as 1 | 2 | 3
      const target = agentTargetForSlot(builder, slot)
      edges.push({
        id: `e:claim-${target.id}`,
        source: idFor.claim(),
        target: target.id,
        type: "chain",
        data: { variant: "animated" },
      })
    }
  }

  const firstCycle = chain.cycles[0]
  if (firstCycle && teamCount > 0) {
    for (let slot = 1; slot <= teamCount; slot++) {
      const source = idFor.agent(slot as 1 | 2 | 3)
      edges.push({
        id: `e:${source}-${firstCycle.id}`,
        source,
        target: firstCycle.id,
        type: "chain",
        data: { variant: edgeVariantBetween(undefined, firstCycle) },
      })
    }
  }

  const currentN = currentCycleN(chain.cycles)
  for (let i = 0; i < chain.cycles.length - 1; i++) {
    const from = chain.cycles[i]
    const to = chain.cycles[i + 1]
    edges.push({
      id: `e:${from.id}-${to.id}`,
      source: from.id,
      target: to.id,
      type: "chain",
      data: { variant: edgeVariantBetween(from, to, currentN) },
    })
  }

  if (chain.nextPlaceholder) {
    const placeholderId = idFor.placeholder()
    const source = placeholderSourceId(chain.cycles, builder, teamCount)
    if (source) {
      edges.push({
        id: `e:${source}-${placeholderId}`,
        source,
        target: placeholderId,
        type: "chain",
        data: { variant: "animated" },
      })
    }
  }

  return edges
}

function placeholderSourceId(
  cycles: CycleStep[],
  builder: Pick<BuilderSnapshot, "focalClaim">,
  teamCount: number,
): string | null {
  const tail = cycles[cycles.length - 1]
  if (tail) return tail.id
  if (teamCount > 0) return idFor.agent(Math.min(2, teamCount) as 1 | 2 | 3)
  if (builder.focalClaim != null) return idFor.claim()
  return idFor.research()
}

function edgeVariantBetween(
  from: CycleStep | undefined,
  to: CycleStep,
  currentN?: number,
): CanvasEdgeVariant {
  if (to.status === "running") return "animated"
  if (to.status === "faded" || (from && from.status === "faded")) return "faded"
  if (currentN != null && to.n < currentN) return "faded"
  if (to.status === "done") return "solid"
  if (to.status === "idle") return "animated"
  return "animated"
}

function currentCycleN(cycles: CycleStep[]): number {
  if (cycles.length === 0) return 0
  return cycles[cycles.length - 1].n
}

function isAgentSlot(node: CanvasNode): boolean {
  return (
    node.type === "placeholder" &&
    node.data.kind === "placeholder" &&
    node.data.nextKind === "agent-slot"
  )
}

function widthFor(node: CanvasNode): number {
  if (isAgentSlot(node)) return SLOT_WIDTH
  if (node.type === "research") return RESEARCH_WIDTH
  return NODE_WIDTH
}

function heightFor(node: CanvasNode): number {
  if (node.type === "research") return RESEARCH_HEIGHT
  if (isAgentSlot(node)) return SLOT_HEIGHT
  if (node.type === "placeholder") return PLACEHOLDER_HEIGHT
  return DEFAULT_HEIGHT
}

export function layoutNodes(
  nodes: CanvasNode[],
  edges: CanvasEdge[],
): CanvasNode[] {
  const g = new Dagre.graphlib.Graph()
    .setDefaultEdgeLabel(() => ({}))
    .setGraph({ rankdir: "TB", ranksep: RANKSEP, nodesep: NODESEP })

  for (const n of nodes) {
    g.setNode(n.id, { width: widthFor(n), height: heightFor(n) })
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target)
  }
  Dagre.layout(g)

  return nodes.map((n) => {
    const pos = g.node(n.id)
    if (!pos) return n
    const w = widthFor(n)
    const h = heightFor(n)
    return {
      ...n,
      position: { x: pos.x - w / 2, y: pos.y - h / 2 },
    }
  })
}
