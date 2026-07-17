import { z } from "zod"

import { PersonaAgentSchema } from "./persona"

export const SteerTypeSchema = z.enum(["emphasize", "reframe"])
export const EvidenceWeightSchema = z.enum([
  "strengthens",
  "weakens",
  "refines",
  "disputed",
  "unrelated",
])
export const TurnActionSchema = z.enum(["challenge", "support", "concede"])
export const AgentPhaseSchema = z.enum(["proposal", "rebuttal", "refinement"])
export const CycleStatusSchema = z.enum(["pending", "running", "complete"])
export const ClaimTypeSchema = z.enum([
  "descriptive",
  "comparative",
  "associative",
  "causal",
  "predictive",
])

export const SteerSchema = z.object({
  type: SteerTypeSchema,
  text: z.string(),
  agent_id: z.string(),
})

export const AgentResponseSchema = z
  .object({
    evidence_weight: EvidenceWeightSchema.nullable().optional(),
    claim: z.string(),
    rationale: z.string(),
    evidence: z.array(z.string()).default([]),
    conceded_point: z.string().nullable().optional(),
    preserved_point: z.string().nullable().optional(),
    revised_position: z.string().nullable().optional(),
    target_id: z.string().nullable().optional(),
    message: z.string(),
    action: TurnActionSchema.nullable().optional(),
  })
  .passthrough()

export const AgentTurnSchema = z
  .object({
    turn_id: z.string(),
    agent_id: z.string(),
    phase: AgentPhaseSchema,
    cycle: z.number().int().default(1),
    response: AgentResponseSchema,
    created_at: z.string(),
  })
  .passthrough()

export const EvidenceSnippetSchema = z
  .object({
    corpus_id: z.string(),
    title: z.string().default(""),
    section: z.string().nullable().optional(),
    text: z.string(),
    score: z.number().nullable().optional(),
    tier: z.string(),
  })
  .passthrough()

export const EvidenceSetSchema = z.object({
  snippets: z.array(EvidenceSnippetSchema).default([]),
})

export const StudyDesignSchema = z
  .object({
    context: z.string(),
    exposure: z.string(),
    comparator: z.string(),
    outcome: z.string(),
    measure: z.string(),
  })
  .passthrough()

export const HypothesisSchema = z
  .object({
    id: z.string().default(""),
    claim_type: ClaimTypeSchema,
    proposition: z.string(),
    causal_chain: z.string(),
    study_design: StudyDesignSchema,
    warrant: z.string(),
    falsifier: z.string(),
    grounding: z.array(z.string()).default([]),
    contributing_agents: z.array(z.string()).default([]),
  })
  .passthrough()

export const BestCandidateSchema = z.object({
  candidate_id: z.string(),
  reason: z.string(),
})

export const MetaReviewSchema = z
  .object({
    problem: z.string(),
    previous_work: z.string(),
    reasoning: z.string(),
    hypothesis: z.string(),
    best_id: z.string().default(""),
  })
  .passthrough()

export const SynthesisSchema = z
  .object({
    phase: z.string().default("synthesis"),
    cycle: z.number().int().default(1),
    hypotheses: z.array(HypothesisSchema).default([]),
    best: BestCandidateSchema.nullable().optional(),
    meta_review: MetaReviewSchema.nullable().optional(),
  })
  .passthrough()

export const CycleSchema = z
  .object({
    cycle_id: z.string(),
    cycle: z.number().int().default(1),
    focal_claim: z.string(),
    problem: z.string().default(""),
    agent_ids: z.array(z.string()).default([]),
    status: CycleStatusSchema,
    steers: z.array(SteerSchema).default([]),
    turns: z.array(AgentTurnSchema).default([]),
    evidence: z.record(z.string(), EvidenceSetSchema).default({}),
    assessment: z.unknown().nullable().optional(),
    adjudication: z.unknown().nullable().optional(),
    synthesis: SynthesisSchema.nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .passthrough()

export const DebateSchema = z
  .object({
    debate_id: z.string(),
    focal_claim: z.string(),
    agents: z.array(PersonaAgentSchema),
    cycle: CycleSchema.nullable().optional(),
    hypotheses: z.array(HypothesisSchema).default([]),
    created_at: z.string(),
  })
  .passthrough()

export type SteerType = z.infer<typeof SteerTypeSchema>
export type EvidenceWeight = z.infer<typeof EvidenceWeightSchema>
export type TurnAction = z.infer<typeof TurnActionSchema>
export type AgentPhase = z.infer<typeof AgentPhaseSchema>
export type ClaimType = z.infer<typeof ClaimTypeSchema>
export type Steer = z.infer<typeof SteerSchema>
export type AgentResponse = z.infer<typeof AgentResponseSchema>
export type AgentTurn = z.infer<typeof AgentTurnSchema>
export type EvidenceSnippet = z.infer<typeof EvidenceSnippetSchema>
export type EvidenceSet = z.infer<typeof EvidenceSetSchema>
export type StudyDesign = z.infer<typeof StudyDesignSchema>
export type Hypothesis = z.infer<typeof HypothesisSchema>
export type BestCandidate = z.infer<typeof BestCandidateSchema>
export type MetaReview = z.infer<typeof MetaReviewSchema>
export type Synthesis = z.infer<typeof SynthesisSchema>
export type Cycle = z.infer<typeof CycleSchema>
export type Debate = z.infer<typeof DebateSchema>
