"use client"

import { useMutation } from "@tanstack/react-query"

import { useSelectionStore } from "@/features/hypo-canvas/selection-store"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { RunMode } from "@/store/agent-builder"
import { PipelineStateSchema, type PipelineState } from "@/types/query"

async function createQuery(
  query: string,
  mode: RunMode,
): Promise<PipelineState> {
  return fetcher("/api/query", PipelineStateSchema, {
    method: "POST",
    body: JSON.stringify({ query, mode, condition: "mars" }),
  })
}

export function useCreateQuery() {
  return useMutation({
    mutationFn: async (text: string) => {
      const {
        researchProblemCommitted: commit,
        focalClaimSet,
        pipelineStagesReset,
        pipelineStageSet,
        mode,
      } = useAgentBuilderStore.getState()

      pipelineStagesReset()
      focalClaimSet(null)
      useSelectionStore.getState().nodeSelected(null)

      const state = await createQuery(text, mode)
      commit(text, state.query_id, "mars")
      pipelineStageSet("extract", "running")
      return { id: state.query_id, text }
    },
    onError: (err) => {
      console.error("[create-query] onError", err)
    },
  })
}
