"use client"

import { useMutation } from "@tanstack/react-query"

import { useSelectionStore } from "@/features/hypo-canvas/selection-store"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"
import { PipelineStateSchema } from "@/types/query"

export function useCreateBaseline() {
  return useMutation({
    mutationFn: async ({
      text,
      testMode = false,
    }: {
      text: string
      testMode?: boolean
    }) => {
      const builder = useAgentBuilderStore.getState()
      builder.researchProblemCleared()
      builder.pipelineStagesReset()
      useSelectionStore.getState().nodeSelected(null)
      useBaselineStore.getState().reset()

      const state = await fetcher("/api/query", PipelineStateSchema, {
        method: "POST",
        body: JSON.stringify({
          query: text,
          mode: "manual",
          condition: "baseline",
          test_mode: testMode,
        }),
      })

      builder.modeSet("manual")
      builder.researchProblemCommitted(text, state.query_id, "baseline")
      builder.pipelineStageSet("extract", "running")
      useBaselineStore.getState().sessionStarted(testMode)
      return state
    },
  })
}
