"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { DebateSchema, type Debate } from "@/types/debate"

async function createDebate(
  focal_claim: string,
  agents: unknown[],
  query_id: string,
): Promise<Debate> {
  return fetcher("/api/debate", DebateSchema, {
    method: "POST",
    body: JSON.stringify({ focal_claim, agents, query_id }),
  })
}

function findRootCycleId(debate: Debate): string | null {
  for (const [cid, cycle] of Object.entries(debate.cycles)) {
    if (!cycle.parent_cycle_id) return cid
  }
  return null
}

export function useCreateDebate() {
  return useMutation({
    mutationFn: async () => {
      const { focalClaim, team, queryId } = useAgentBuilderStore.getState()
      if (!focalClaim) throw new Error("focal claim required")
      if (team.length === 0) throw new Error("at least one agent required")
      if (!queryId) throw new Error("query_id required — run the research query first")
      const debate = await createDebate(focalClaim, team, queryId)
      const rootId = findRootCycleId(debate)
      if (!rootId) throw new Error("debate created without a root cycle")
      useDebateStore
        .getState()
        .debateCreated(debate.debate_id, { s0: rootId }, debate.cycles)
      return { debate, rootId }
    },
    onError: (err) => {
      console.error("[create-debate] error", err)
    },
  })
}
