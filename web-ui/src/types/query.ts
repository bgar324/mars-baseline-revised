import { z } from "zod"

export const StageNameSchema = z.enum([
  "extract",
  "retrieve",
  "cluster",
  "persona",
  "debate",
])

export const StageStatusSchema = z.enum([
  "pending",
  "running",
  "complete",
  "skipped",
  "failed",
])

export const StageNodeSchema = z
  .object({
    stage: StageNameSchema,
    status: StageStatusSchema,
    result: z.unknown().nullable().optional(),
    error: z.string().nullable().optional(),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
  })
  .passthrough()

export const PipelineStateSchema = z
  .object({
    query_id: z.string(),
    stages: z.record(StageNameSchema, StageNodeSchema),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .passthrough()

export const PipelineEventSchema = z.object({
  event: z.string(),
  query_id: z.string(),
  stage: StageNameSchema.nullable().optional(),
  step: z.string().nullable().optional(),
  payload: z.unknown().optional(),
  timestamp: z.string(),
})

export const ExtractedQuerySchema = z
  .object({
    raw_text: z.string(),
    claim: z.string(),
  })
  .passthrough()

export const QueryRequestSchema = z.object({
  query: z.string().min(1),
})

export type StageName = z.infer<typeof StageNameSchema>
export type StageStatus = z.infer<typeof StageStatusSchema>
export type PipelineState = z.infer<typeof PipelineStateSchema>
export type PipelineEvent = z.infer<typeof PipelineEventSchema>
export type ExtractedQuery = z.infer<typeof ExtractedQuerySchema>
export type QueryRequest = z.infer<typeof QueryRequestSchema>
