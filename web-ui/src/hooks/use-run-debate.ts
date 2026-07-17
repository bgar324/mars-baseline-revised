"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"
import { PipelineStateSchema, type PipelineState } from "@/types/query"

async function runDebate(
  queryId: string,
  personas: PersonaAgent[],
  papers: Paper[],
): Promise<PipelineState> {
  return fetcher(`/api/query/${queryId}/debate`, PipelineStateSchema, {
    method: "POST",
    body: JSON.stringify({ personas, papers }),
  })
}

export function useRunDebate() {
  return useMutation({
    mutationFn: async (personas: PersonaAgent[]) => {
      const { queryId, pipelineStageSet } = useAgentBuilderStore.getState()
      if (!queryId) throw new Error("no active query")
      const papers = useBaselineStore.getState().manualPapers
      const state = await runDebate(queryId, personas, papers)
      pipelineStageSet("debate", "running")
      return state
    },
    onError: (err) => {
      console.error("[run-debate] onError", err)
    },
  })
}
