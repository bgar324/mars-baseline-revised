"use client"

import { useQuery } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PaperListSchema, type Paper } from "@/types/paper"

async function fetchPapers(queryId: string): Promise<Paper[]> {
  return fetcher(`/api/query/${queryId}/papers`, PaperListSchema)
}

export function usePapers() {
  const queryId = useAgentBuilderStore((s) => s.queryId)

  return useQuery({
    queryKey: ["papers", queryId],
    queryFn: () => fetchPapers(queryId!),
    enabled: !!queryId,
    retry: 0,
  })
}
