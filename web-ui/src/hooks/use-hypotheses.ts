"use client"

import { useQuery } from "@tanstack/react-query"

import { clearStaleQuery } from "@/hooks/use-stale-query"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { SynthesisSchema, type Synthesis } from "@/types/debate"

async function fetchHypotheses(queryId: string): Promise<Synthesis> {
  return fetcher(`/api/query/${queryId}/hypotheses`, SynthesisSchema)
}

export function useHypotheses() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const debateStage = useAgentBuilderStore((s) => s.pipelineStages.debate)
  const ready = !!queryId && debateStage === "complete"

  return useQuery({
    queryKey: ["hypotheses", queryId],
    queryFn: async () => {
      try {
        return await fetchHypotheses(queryId!)
      } catch (error) {
        clearStaleQuery(error)
        throw error
      }
    },
    enabled: ready,
    retry: 0,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}
