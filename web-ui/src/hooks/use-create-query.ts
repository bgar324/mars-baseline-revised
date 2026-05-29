"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import {
  PipelineStateSchema,
  type PipelineState,
  type StageName,
} from "@/types/query"

async function createQuery(query: string): Promise<PipelineState> {
  return fetcher("/api/query", PipelineStateSchema, {
    method: "POST",
    body: JSON.stringify({ query }),
  })
}

async function runStage(queryId: string, stage: string): Promise<PipelineState> {
  return fetcher(
    `/api/query/${queryId}/${stage}`,
    PipelineStateSchema,
    { method: "POST" },
  )
}

function assertStageComplete(state: PipelineState, stage: StageName): void {
  const node = state.stages[stage]
  if (!node) {
    console.error(
      "[create-query] missing stage",
      stage,
      "in",
      Object.keys(state.stages),
    )
    throw new Error(`pipeline state missing stage '${stage}'`)
  }
  if (node.status === "failed") {
    console.error("[create-query] stage failed", stage, node.error)
    throw new Error(
      `stage '${stage}' failed: ${node.error ?? "no error message"}`,
    )
  }
  if (node.status !== "complete") {
    console.error("[create-query] stage not complete", stage, node.status)
    throw new Error(
      `stage '${stage}' is '${node.status}'; expected 'complete'`,
    )
  }
  console.log("[create-query] ✓", stage)
}

export function useCreateQuery() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (text: string) => {
      const {
        researchProblemCommitted: commit,
        focalClaimSet,
        pipelineStageSet,
        pipelineStagesReset,
      } = useAgentBuilderStore.getState()

      pipelineStagesReset()
      focalClaimSet(null)

      pipelineStageSet("extract", "running")
      pipelineStageSet("expand", "running")
      const initial = await createQuery(text)
      const id = initial.query_id
      commit(text, id)
      assertStageComplete(initial, "extract")
      pipelineStageSet("extract", "complete")

      const extractResult = initial.stages.extract?.result as
        | { claim?: string }
        | null
        | undefined
      focalClaimSet(extractResult?.claim ?? text)

      assertStageComplete(initial, "expand")
      pipelineStageSet("expand", "complete")

      pipelineStageSet("retrieve", "running")
      const afterRetrieve = await runStage(id, "retrieve")
      assertStageComplete(afterRetrieve, "retrieve")
      pipelineStageSet("retrieve", "complete")

      pipelineStageSet("cluster", "running")
      const afterClusters = await runStage(id, "clusters")
      assertStageComplete(afterClusters, "cluster")
      pipelineStageSet("cluster", "complete")

      pipelineStageSet("persona", "running")
      const afterPersonas = await runStage(id, "personas")
      assertStageComplete(afterPersonas, "persona")
      pipelineStageSet("persona", "complete")

      return { id, text }
    },
    onSuccess: ({ id }) => {
      console.log("[create-query] onSuccess", { id })
      queryClient.invalidateQueries({ queryKey: ["personas", id] })
    },
    onError: (err) => {
      console.error("[create-query] onError", err)
    },
  })
}
