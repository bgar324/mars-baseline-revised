"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PipelineStateSchema, type PipelineState } from "@/types/query"

async function runDebate(
  queryId: string,
  clusterIds: number[],
): Promise<PipelineState> {
  return fetcher(`/api/query/${queryId}/debate`, PipelineStateSchema, {
    method: "POST",
    body: JSON.stringify({ cluster_ids: clusterIds }),
  })
}

export function useRunDebate() {
  return useMutation({
    mutationFn: async (clusterIds: number[]) => {
      const { queryId, pipelineStageSet } = useAgentBuilderStore.getState()
      if (!queryId) throw new Error("no active query")
      const state = await runDebate(queryId, clusterIds)
      pipelineStageSet("debate", "running")
      return state
    },
    onError: (err) => {
      console.error("[run-debate] onError", err)
    },
  })
}
