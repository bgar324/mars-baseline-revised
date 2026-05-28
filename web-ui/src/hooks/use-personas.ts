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

  const q = useQuery({
    queryKey: ["personas", queryId],
    queryFn: () => fetchPersonas(queryId!),
    enabled: !!queryId,
    retry: 0,
  })

  console.log(
    "[personas] queryId=",
    queryId,
    "status=",
    q.status,
    "fetching=",
    q.isFetching,
    "data?",
    !!q.data,
    "len=",
    q.data?.length,
    "error=",
    q.error,
  )

  return q
}
