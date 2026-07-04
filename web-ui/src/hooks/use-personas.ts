"use client"

import { useQuery } from "@tanstack/react-query"

import { fetcher, isStaleQueryError } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PersonaAgentListSchema, type PersonaAgent } from "@/types/persona"

async function fetchPersonas(queryId: string): Promise<PersonaAgent[]> {
  return fetcher(
    `/api/query/${queryId}/persona-pool`,
    PersonaAgentListSchema,
  )
}

export function usePersonas() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const personaStage = useAgentBuilderStore(
    (s) => s.pipelineStages.persona,
  )
  const cached = useAgentBuilderStore((s) => s.personas)
  const personasSet = useAgentBuilderStore((s) => s.personasSet)
  const ready = !!queryId && personaStage === "complete"

  return useQuery({
    queryKey: ["personas", queryId],
    queryFn: async () => {
      try {
        const data = await fetchPersonas(queryId!)
        personasSet(data)
        return data
      } catch (error) {
        if (isStaleQueryError(error)) {
          useAgentBuilderStore.getState().researchProblemCleared()
        }
        throw error
      }
    },
    enabled: ready,
    retry: 0,
    initialData: cached.length > 0 ? cached : undefined,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}
