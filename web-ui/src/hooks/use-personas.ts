"use client"

import { useQuery } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PersonaAgentListSchema, type PersonaAgent } from "@/types/persona"

async function fetchPersonas(queryId: string): Promise<PersonaAgent[]> {
  return fetcher(
    `/api/query/${queryId}/personas`,
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
      const data = await fetchPersonas(queryId!)
      personasSet(data)
      return data
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
