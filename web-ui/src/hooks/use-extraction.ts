"use client"

import { useQuery } from "@tanstack/react-query"

import { clearStaleQuery } from "@/hooks/use-stale-query"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { ExtractedQuerySchema, type ExtractedQuery } from "@/types/query"

async function fetchExtraction(queryId: string): Promise<ExtractedQuery> {
  return fetcher(`/api/query/${queryId}/extraction`, ExtractedQuerySchema)
}

export function useExtraction() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const extractStage = useAgentBuilderStore((s) => s.pipelineStages.extract)
  const focalClaimSet = useAgentBuilderStore((s) => s.focalClaimSet)
  const ready = !!queryId && extractStage === "complete"

  return useQuery({
    queryKey: ["extraction", queryId],
    queryFn: async () => {
      try {
        const data = await fetchExtraction(queryId!)
        focalClaimSet(data.claim)
        return data
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
