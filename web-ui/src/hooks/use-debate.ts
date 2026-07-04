"use client"

import { useQuery } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { DebateSchema, type Debate } from "@/types/debate"

async function fetchDebate(queryId: string): Promise<Debate> {
  return fetcher(`/api/query/${queryId}/debate`, DebateSchema)
}

export function useDebate() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const debateStage = useAgentBuilderStore((s) => s.pipelineStages.debate)
  const running = debateStage === "running"
  const ready = !!queryId && (running || debateStage === "complete")

  return useQuery({
    queryKey: ["debate", queryId],
    queryFn: () => fetchDebate(queryId!),
    enabled: ready,
    retry: 0,
    refetchInterval: running ? 4000 : false,
    staleTime: running ? 0 : Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}
