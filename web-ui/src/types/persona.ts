import { z } from "zod"

export const ReasoningStyleSchema = z.enum([
  "mechanistic",
  "observational",
  "interventional",
  "comparative",
  "theoretical",
  "computational",
  "statistical",
])

export const EvaluationLensSchema = z.enum([
  "internal_validity",
  "external_validity",
  "construct_validity",
  "effect_magnitude",
  "replicability",
  "convergence",
  "predictive_power",
])

export const EvidenceRelationSchema = z.enum([
  "direct",
  "analogical",
  "mixed",
  "ungrounded",
])

export const PersonaAgentSchema = z
  .object({
    cluster_id: z.number().int(),
    name: z.string(),
    framing: z.string(),
    background: z.string(),
    methods_summary: z.string(),
    evidence_relation: EvidenceRelationSchema,
    reasoning_style: ReasoningStyleSchema,
    evaluation_lens: EvaluationLensSchema,
    references: z.array(z.string()),
    instructions: z.array(z.string()).min(1),
    constraints: z.string().nullable().optional(),
  })
  .passthrough()

export const PersonaAgentListSchema = z.array(PersonaAgentSchema)

export type ReasoningStyle = z.infer<typeof ReasoningStyleSchema>
export type EvaluationLens = z.infer<typeof EvaluationLensSchema>
export type EvidenceRelation = z.infer<typeof EvidenceRelationSchema>
export type PersonaAgent = z.infer<typeof PersonaAgentSchema>

export const REASONING_STYLE_DESCRIPTIONS: Record<ReasoningStyle, string> = {
  mechanistic: "Looks for the processes driving outcomes.",
  observational: "Reads patterns from real-world data.",
  interventional: "Tests claims by isolating causes.",
  comparative: "Contrasts groups and conditions for differences.",
  theoretical: "Reasons from first principles and prior theory.",
  computational: "Builds models and simulations to probe ideas.",
  statistical: "Weighs aggregate trends and uncertainty.",
}

export const EVALUATION_LENS_DESCRIPTIONS: Record<EvaluationLens, string> = {
  internal_validity: "Pushes on whether causal claims hold inside the study.",
  external_validity: "Asks whether findings generalize beyond the sample.",
  construct_validity: "Checks that measures capture the right thing.",
  effect_magnitude: "Weighs how large effects really are.",
  replicability: "Demands convergent results across studies.",
  convergence: "Looks for multiple methods agreeing.",
  predictive_power: "Judges claims by their forecasting accuracy.",
}
