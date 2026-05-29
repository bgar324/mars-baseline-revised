"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { AgentTurnSchema, type AgentTurn, type Steer } from "@/types/debate"

type ProposeArgs = {
  debateId: string
  backendCycleId: string
  canvasCycleId: string
  agentId: string
  steers: Steer[]
}

async function propose(
  debateId: string,
  cycleId: string,
  agentId: string,
  steers: Steer[],
): Promise<AgentTurn> {
  return fetcher(
    `/api/debate/${debateId}/cycles/${cycleId}/propose`,
    AgentTurnSchema,
    {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, steers }),
    },
  )
}

export function useProposeTurn() {
  return useMutation({
    mutationFn: async ({
      debateId,
      backendCycleId,
      canvasCycleId,
      agentId,
      steers,
    }: ProposeArgs) => {
      const turn = await propose(debateId, backendCycleId, agentId, steers)
      useDebateStore.getState().proposalSet(canvasCycleId, agentId, turn)
      return turn
    },
    onError: (err) => console.error("[propose-turn]", err),
  })
}
