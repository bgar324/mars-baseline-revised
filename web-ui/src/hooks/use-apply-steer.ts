"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { CycleSchema, type Cycle, type Steer } from "@/types/debate"

async function setSteers(
  debateId: string,
  cycleId: string,
  steers: Steer[],
): Promise<Cycle> {
  return fetcher(
    `/api/debate/${debateId}/cycles/${cycleId}/steers`,
    CycleSchema,
    { method: "PUT", body: JSON.stringify(steers) },
  )
}

export function useApplySteer() {
  return useMutation({
    mutationFn: async ({
      debateId,
      backendCycleId,
      steers,
    }: {
      debateId: string
      backendCycleId: string
      steers: Steer[]
    }) => {
      const status =
        useDebateStore.getState().cyclesByBackendId[backendCycleId]?.status
      if (status === "running" || status === "awaiting") {
        return null
      }
      const cycle = await setSteers(debateId, backendCycleId, steers)
      useDebateStore.getState().cyclePopulated(cycle.cycle_id, cycle)
      return cycle
    },
    onError: (err) => {
      console.error("[apply-steer]", err)
    },
  })
}
