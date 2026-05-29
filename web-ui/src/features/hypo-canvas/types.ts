export type CycleKind = "steer" | "debate"

export type CycleStatus = "idle" | "running" | "done" | "faded"

export type CycleStep =
  | { id: `s${number}`; kind: "steer"; n: number; status: CycleStatus }
  | { id: `d${number}`; kind: "debate"; n: number; status: CycleStatus }

export type NextPlaceholder =
  | { kind: "steer"; n: number }
  | { kind: "debate"; n: number }

import type { PersonaAgent } from "@/types/persona"
import type { StageName, StageStatus } from "@/types/query"

export type BuilderSnapshot = {
  query: string | null
  focalClaim: string | null
  pipelineStages: Partial<Record<StageName, StageStatus>>
  team: PersonaAgent[]
}

export type CanvasNodeKind =
  | "research"
  | "claim"
  | "agent"
  | "steer"
  | "debate"
  | "placeholder"

export type ResearchStageStatus = "pending" | "running" | "done"

export type ResearchStage = {
  key: StageName
  name: string
  status: ResearchStageStatus
  description?: string
  detail?: string
}

export type CanvasNodeData =
  | { kind: "research"; query: string | null; stages?: ResearchStage[] }
  | { kind: "claim"; focalClaim: string | null }
  | {
      kind: "agent"
      clusterId: number
      name: string
      reasoningStyle: string
      slot: 1 | 2 | 3
      persona: PersonaAgent
    }
  | { kind: "steer"; n: number; status: CycleStatus }
  | { kind: "debate"; n: number; status: CycleStatus }
  | {
      kind: "placeholder"
      nextKind: CycleKind | "agent-slot"
      n: number
      slot?: 1 | 2 | 3
      disabled: boolean
      blockedReason: string | null
    }

export type CanvasNode = {
  id: string
  type: CanvasNodeKind
  position: { x: number; y: number }
  data: CanvasNodeData
}

export type CanvasEdgeVariant = "solid" | "dashed" | "animated" | "faded"

export type CanvasEdge = {
  id: string
  source: string
  target: string
  type: "chain"
  data: { variant: CanvasEdgeVariant }
}
