import assert from "node:assert/strict"
import test from "node:test"

import { PipelineStateSchema } from "./query"

const timestamp = "2026-07-18T05:00:00Z"

function stage(name: "extract" | "retrieve" | "cluster" | "persona" | "debate") {
  return { stage: name, status: "pending" as const, steps: {} }
}

test("accepts the debate-only state returned by the baseline API", () => {
  const result = PipelineStateSchema.parse({
    query_id: "baseline-query",
    stages: { debate: stage("debate") },
    created_at: timestamp,
    updated_at: timestamp,
  })

  assert.equal(result.stages.debate?.status, "pending")
  assert.equal(result.stages.extract, undefined)
})

test("continues to accept the complete full-MARS stage map", () => {
  const stages = {
    extract: stage("extract"),
    retrieve: stage("retrieve"),
    cluster: stage("cluster"),
    persona: stage("persona"),
    debate: stage("debate"),
  }

  const result = PipelineStateSchema.safeParse({
    query_id: "mars-query",
    stages,
    created_at: timestamp,
    updated_at: timestamp,
  })

  assert.equal(result.success, true)
})

test("still rejects malformed stages that are present", () => {
  const result = PipelineStateSchema.safeParse({
    query_id: "broken-query",
    stages: { debate: { status: "pending", steps: {} } },
    created_at: timestamp,
    updated_at: timestamp,
  })

  assert.equal(result.success, false)
})
