import { z } from "zod"

export const StageNameSchema = z.enum([
  "extract",
  "expand",
  "retrieve",
  "cluster",
  "persona",
])

export const StageStatusSchema = z.enum([
  "pending",
  "running",
  "complete",
  "failed",
])

export const StageNodeSchema = z.object({
  stage: StageNameSchema,
  status: StageStatusSchema,
  result: z.unknown().nullable().optional(),
  error: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
})

export const PipelineStateSchema = z.object({
  query_id: z.string(),
  stages: z.record(StageNameSchema, StageNodeSchema),
  created_at: z.string(),
  updated_at: z.string(),
})

export const QueryRequestSchema = z.object({
  query: z.string().min(1),
})

export type StageName = z.infer<typeof StageNameSchema>
export type StageStatus = z.infer<typeof StageStatusSchema>
export type PipelineState = z.infer<typeof PipelineStateSchema>
export type QueryRequest = z.infer<typeof QueryRequestSchema>
