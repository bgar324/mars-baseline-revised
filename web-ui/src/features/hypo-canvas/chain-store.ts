import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type {
  CycleStatus,
  CycleStep,
  NextPlaceholder,
} from "./types"

type ChainState = {
  cycles: CycleStep[]
  currentCycleId: string | null
  nextPlaceholder: NextPlaceholder | null
  blockedReason: string | null
}

type ChainActions = {
  steerAdvanced: (n: number) => void
  debateAdvanced: (n: number) => void
  cycleStatusChanged: (id: string, status: CycleStatus) => void
  placeholderSet: (
    next: NextPlaceholder | null,
    blockedReason?: string | null,
  ) => void
  reset: () => void
}

const initial: ChainState = {
  cycles: [],
  currentCycleId: null,
  nextPlaceholder: null,
  blockedReason: null,
}

export const useChainStore = create<ChainState & ChainActions>()(
  persist(
    (set) => ({
      ...initial,

      steerAdvanced: (n) =>
        set((state) => {
          const id = `s${n}` as const
          if (state.cycles.some((c) => c.id === id)) return state
          const step: CycleStep = { id, kind: "steer", n, status: "idle" }
          return {
            cycles: [...state.cycles, step],
            currentCycleId: id,
          }
        }),

      debateAdvanced: (n) =>
        set((state) => {
          const id = `d${n}` as const
          if (state.cycles.some((c) => c.id === id)) return state
          const step: CycleStep = { id, kind: "debate", n, status: "idle" }
          return {
            cycles: [...state.cycles, step],
            currentCycleId: id,
          }
        }),

      cycleStatusChanged: (id, status) =>
        set((state) => ({
          cycles: state.cycles.map((c) =>
            c.id === id ? ({ ...c, status } as CycleStep) : c,
          ),
        })),

      placeholderSet: (next, blockedReason = null) =>
        set({ nextPlaceholder: next, blockedReason }),

      reset: () => set({ ...initial }),
    }),
    {
      name: "hypo-chain",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        cycles: s.cycles,
        currentCycleId: s.currentCycleId,
        nextPlaceholder: s.nextPlaceholder,
        blockedReason: s.blockedReason,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return
        state.cycles = state.cycles.map((c) =>
          c.status === "running" ? { ...c, status: "faded" } : c,
        ) as CycleStep[]
      },
    },
  ),
)
