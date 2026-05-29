"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { CycleSchema, type Cycle } from "@/types/debate"

async function runCycle(debateId: string, cycleId: string): Promise<Cycle> {
  return fetcher(`/api/debate/${debateId}/cycles/${cycleId}/run`, CycleSchema, {
    method: "POST",
  })
}

export function useRunCycle() {
  return useMutation({
    mutationFn: async ({
      debateId,
      cycleId,
    }: {
      debateId: string
      cycleId: string
    }) => {
      const cycle = await runCycle(debateId, cycleId)
      useDebateStore.getState().cyclePopulated(cycle.cycle_id, cycle)
      return cycle
    },
    onError: (err) => {
      console.error("[run-cycle] error", err)
    },
  })
}
