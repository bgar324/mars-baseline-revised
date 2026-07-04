"use client"

import { useQuery } from "@tanstack/react-query"

import { clearStaleQuery } from "@/hooks/use-stale-query"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PaperListSchema, type Paper } from "@/types/paper"

async function fetchPapers(queryId: string): Promise<Paper[]> {
  return fetcher(`/api/query/${queryId}/papers`, PaperListSchema)
}

export function usePapers() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const retrieveStage = useAgentBuilderStore(
    (s) => s.pipelineStages.retrieve,
  )
  const ready = !!queryId && retrieveStage === "complete"

  return useQuery({
    queryKey: ["papers", queryId],
    queryFn: async () => {
      try {
        return await fetchPapers(queryId!)
      } catch (error) {
        clearStaleQuery(error)
        throw error
      }
    },
    enabled: ready,
    retry: 0,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}
