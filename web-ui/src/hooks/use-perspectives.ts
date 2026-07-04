"use client"

import { useQuery } from "@tanstack/react-query"
import { z } from "zod"

import { clearStaleQuery } from "@/hooks/use-stale-query"
import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"

const PerspectivesSchema = z.array(z.number().int())

async function fetchPerspectives(queryId: string): Promise<number[]> {
  return fetcher(`/api/query/${queryId}/perspectives`, PerspectivesSchema)
}

export function usePerspectives() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const personaStage = useAgentBuilderStore((s) => s.pipelineStages.persona)
  const ready = !!queryId && personaStage === "complete"

  return useQuery({
    queryKey: ["perspectives", queryId],
    queryFn: async () => {
      try {
        return await fetchPerspectives(queryId!)
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
