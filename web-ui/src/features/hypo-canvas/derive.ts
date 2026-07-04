import Dagre from "@dagrejs/dagre"

import type { StageName } from "@/types/query"

import type {
  BuilderSnapshot,
  CanvasEdge,
  CanvasEdgeVariant,
  CanvasNode,
  ResearchStage,
} from "./types"

const NODE_WIDTH = 288
const RESEARCH_WIDTH = 448
const RESEARCH_HEIGHT = 260
const DEFAULT_HEIGHT = 120
const RANKSEP = 140
const NODESEP = 80

const STAGE_ORDER: StageName[] = ["extract", "retrieve", "cluster", "persona"]
const STAGE_LABEL: Record<StageName, string> = {
  extract: "Extract focal claim",
  retrieve: "Retrieve references",
  cluster: "Compute clusters",
  persona: "Generate persona pool",
  debate: "Run debate",
}
const STAGE_DESCRIPTION: Record<StageName, string> = {
  extract: "Extracting and decomposing research problem...",
  retrieve: "Retrieving supporting papers from Semantic Scholar...",
  cluster: "Clustering papers by theme...",
  persona: "Building researcher personas from clusters...",
  debate: "Agents debate the focal claim...",
}

export const idFor = {
  research: () => "research" as const,
  claim: () => "claim" as const,
  agent: (clusterId: number) => `agent-${clusterId}` as const,
  debate: () => "debate" as const,
}

const ORIGIN = { x: 0, y: 0 } as const

function deriveResearchStages(
  builder: BuilderSnapshot,
): ResearchStage[] | undefined {
  const stages: ResearchStage[] = STAGE_ORDER.map((stage) => {
    const base = {
      key: stage,
      name: STAGE_LABEL[stage],
      description: STAGE_DESCRIPTION[stage],
    }
    const status = builder.pipelineStages[stage]
    if (status === "complete" || status === "skipped")
      return { ...base, status: "done" }
    if (status === "running") return { ...base, status: "running" }
    if (status === "failed")
      return { ...base, status: "failed", error: builder.stageErrors[stage] }
    return { ...base, status: "pending" }
  })
  const anyActive = stages.some((s) => s.status !== "pending")
  return anyActive ? stages : undefined
}

function hasDebateNode(builder: BuilderSnapshot): boolean {
  const status = builder.pipelineStages.debate
  return status === "running" || status === "complete" || status === "failed"
}

export function deriveNodes(builder: BuilderSnapshot): CanvasNode[] {
  const nodes: CanvasNode[] = []

  nodes.push({
    id: idFor.research(),
    type: "research",
    position: { ...ORIGIN },
    data: {
      kind: "research",
      query: builder.query,
      stages: deriveResearchStages(builder),
    },
  })

  if (builder.focalClaim != null) {
    nodes.push({
      id: idFor.claim(),
      type: "claim",
      position: { ...ORIGIN },
      data: { kind: "claim", focalClaim: builder.focalClaim },
    })

    for (const persona of builder.personas) {
      nodes.push({
        id: idFor.agent(persona.cluster_id),
        type: "agent",
        position: { ...ORIGIN },
        data: {
          kind: "agent",
          clusterId: persona.cluster_id,
          name: persona.name,
          reasoningStyle: persona.reasoning_style,
          persona,
        },
      })
    }
  }

  if (hasDebateNode(builder)) {
    nodes.push({
      id: idFor.debate(),
      type: "debate",
      position: { ...ORIGIN },
      data: { kind: "debate" },
    })
  }

  return nodes
}

export function deriveEdges(builder: BuilderSnapshot): CanvasEdge[] {
  const edges: CanvasEdge[] = []
  if (builder.focalClaim == null) return edges

  edges.push({
    id: "e:research-claim",
    source: idFor.research(),
    target: idFor.claim(),
    type: "chain",
    data: { variant: "solid" },
  })

  const debatePresent = hasDebateNode(builder)
  const debateRunning = builder.pipelineStages.debate === "running"
  const debateVariant: CanvasEdgeVariant = debateRunning ? "animated" : "solid"

  for (const persona of builder.personas) {
    const agentId = idFor.agent(persona.cluster_id)
    edges.push({
      id: `e:claim-${agentId}`,
      source: idFor.claim(),
      target: agentId,
      type: "chain",
      data: { variant: "solid" },
    })
    if (debatePresent) {
      edges.push({
        id: `e:${agentId}-debate`,
        source: agentId,
        target: idFor.debate(),
        type: "chain",
        data: { variant: debateVariant },
      })
    }
  }

  return edges
}

function widthFor(node: CanvasNode): number {
  if (node.type === "research") return RESEARCH_WIDTH
  return NODE_WIDTH
}

function heightFor(node: CanvasNode): number {
  if (node.type === "research") return RESEARCH_HEIGHT
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
