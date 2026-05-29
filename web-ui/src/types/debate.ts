import { z } from "zod"

import { PersonaAgentSchema } from "./persona"

export const SteerTypeSchema = z.enum(["emphasize", "reframe"])
export const TurnTypeSchema = z.enum(["propose", "respond", "refine"])
export const ResponseActionSchema = z.enum(["challenge", "support", "concede"])
export const DebateActionSchema = z.enum(["accept", "branch", "close"])
export const CycleStatusSchema = z.enum([
  "pending",
  "running",
  "awaiting",
  "complete",
])

export const CitationSchema = z.object({
  paper_id: z.string(),
  span: z.string().nullable().optional(),
})

export const SteerSchema = z.object({
  type: SteerTypeSchema,
  text: z.string(),
  agent_id: z.string(),
  cycle_id: z.string(),
})

export const AgentTurnSchema = z.object({
  turn_id: z.string(),
  cycle_id: z.string(),
  agent_id: z.string(),
  turn_type: TurnTypeSchema,
  response_action: ResponseActionSchema.nullable().optional(),
  target_turn_id: z.string().nullable().optional(),
  claim: z.string(),
  rationale: z.string(),
  evidence: z.array(CitationSchema).default([]),
  message: z.string(),
  created_at: z.string(),
})

export const BranchSchema = z.object({
  label: z.string(),
  rationale: z.string(),
  outcome: z.enum(["question", "disagreement", "assumption"]),
  focal_claim: z.string(),
  agents: z.array(z.string()).nullable().optional(),
})

export const DebateSynthesisSchema = z.object({
  cycle_id: z.string(),
  points_of_agreement: z.array(z.string()).default([]),
  points_of_disagreement: z.array(z.string()).default([]),
  questions: z.array(z.string()).default([]),
  candidate_hypotheses: z.array(z.string()).default([]),
  branches: z.array(BranchSchema).default([]),
})

export const CycleSchema = z.object({
  cycle_id: z.string(),
  parent_cycle_id: z.string().nullable().optional(),
  focal_claim: z.string(),
  agent_ids: z.array(z.string()),
  turns: z.array(AgentTurnSchema).default([]),
  synthesis: DebateSynthesisSchema.nullable().optional(),
  status: CycleStatusSchema,
  steers: z.array(SteerSchema).default([]),
  created_at: z.string(),
  updated_at: z.string(),
})

export const DebateSchema = z.object({
  debate_id: z.string(),
  root_focal_claim: z.string(),
  agents: z.array(PersonaAgentSchema),
  cycles: z.record(z.string(), CycleSchema),
  hypotheses: z.array(z.string()).default([]),
  created_at: z.string(),
})

export const DebateRequestSchema = z.object({
  focal_claim: z.string(),
  agents: z.array(PersonaAgentSchema),
  cluster_papers: z.record(z.string(), z.array(z.unknown())).default({}),
})

export const DebateEventTypeSchema = z.enum([
  "debate.started",
  "cycle.started",
  "turn.produced",
  "cycle.synthesized",
  "stance.updated",
  "cycle.awaiting",
  "hypothesis.accepted",
  "cycle.closed",
  "cycle.branched",
  "corpus.expanded",
])

export const DebateEventSchema = z.object({
  event: DebateEventTypeSchema,
  debate_id: z.string(),
  cycle_id: z.string().nullable().optional(),
  payload: z.record(z.string(), z.unknown()).default({}),
  timestamp: z.string(),
})

export type SteerType = z.infer<typeof SteerTypeSchema>
export type Steer = z.infer<typeof SteerSchema>
export type AgentTurn = z.infer<typeof AgentTurnSchema>
export type Cycle = z.infer<typeof CycleSchema>
export type Debate = z.infer<typeof DebateSchema>
export type DebateRequest = z.infer<typeof DebateRequestSchema>
export type DebateEventType = z.infer<typeof DebateEventTypeSchema>
export type DebateEvent = z.infer<typeof DebateEventSchema>
