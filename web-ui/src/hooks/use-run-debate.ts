"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"
import { PipelineStateSchema, type PipelineState } from "@/types/query"

async function createBaseline(question: string): Promise<PipelineState> {
  return fetcher("/api/query", PipelineStateSchema, {
    method: "POST",
    body: JSON.stringify({
      query: question,
      mode: "manual",
      condition: "baseline",
      test_mode: false,
    }),
  })
}

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
    mutationFn: async (
      input:
        | PersonaAgent[]
        | { personas: PersonaAgent[]; question: string },
    ) => {
      const builder = useAgentBuilderStore.getState()
      const baseline = useBaselineStore.getState()
      const personas = Array.isArray(input) ? input : input.personas
      const question = Array.isArray(input)
        ? (builder.committed ?? builder.draft).trim()
        : input.question
      let queryId = builder.queryId

      if (!queryId) {
        if (!question) throw new Error("research question is required")
        const state = await createBaseline(question)
        queryId = state.query_id
        builder.modeSet("manual")
        builder.researchProblemCommitted(question, queryId, "baseline")
        baseline.sessionStarted(false)
      }

      const papers = baseline.manualPapers
      const state = await runDebate(queryId, personas, papers)
      builder.pipelineStageSet("debate", "running")
      return state
    },
    onError: (err) => {
      console.error("[run-debate] onError", err)
    },
  })
}
