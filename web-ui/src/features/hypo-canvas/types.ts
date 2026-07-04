import type { PersonaAgent } from "@/types/persona"
import type { StageName, StageStatus } from "@/types/query"

export type BuilderSnapshot = {
  query: string | null
  focalClaim: string | null
  pipelineStages: Partial<Record<StageName, StageStatus>>
  stageErrors: Partial<Record<StageName, string>>
  personas: PersonaAgent[]
}

export type CanvasNodeKind = "research" | "claim" | "agent" | "debate"

export type ResearchStageStatus = "pending" | "running" | "done" | "failed"

export type ResearchStage = {
  key: StageName
  name: string
  status: ResearchStageStatus
  description?: string
  detail?: string
  error?: string
}

export type CanvasNodeData =
  | { kind: "research"; query: string | null; stages?: ResearchStage[] }
  | { kind: "claim"; focalClaim: string | null }
  | {
      kind: "agent"
      clusterId: number
      name: string
      reasoningStyle: string
      persona: PersonaAgent
    }
  | { kind: "debate" }

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
