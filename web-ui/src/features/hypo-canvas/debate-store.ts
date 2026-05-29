import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import { AgentTurnSchema, type AgentTurn, type Cycle, type DebateEvent, type Steer } from "@/types/debate"

type DebateState = {
  debateId: string | null
  canvasToBackend: Record<string, string>
  cyclesByBackendId: Record<string, Cycle>
  chips: Record<string, Record<string, Steer[]>>
  proposals: Record<string, Record<string, AgentTurn>>
  eventLog: DebateEvent[]
}

type DebateActions = {
  debateCreated: (
    debateId: string,
    canvasToBackend: Record<string, string>,
    initialCycles: Record<string, Cycle>,
  ) => void
  cycleMapped: (canvasCycleId: string, backendCycleId: string) => void
  cyclePopulated: (backendCycleId: string, cycle: Cycle) => void
  chipAdded: (canvasCycleId: string, agentId: string, steer: Steer) => void
  chipRemoved: (
    canvasCycleId: string,
    agentId: string,
    steerIndex: number,
  ) => void
  proposalSet: (
    canvasCycleId: string,
    agentId: string,
    turn: AgentTurn,
  ) => void
  eventReceived: (event: DebateEvent) => void
  reset: () => void
}

const initial: DebateState = {
  debateId: null,
  canvasToBackend: {},
  cyclesByBackendId: {},
  chips: {},
  proposals: {},
  eventLog: [],
}

export const useDebateStore = create<DebateState & DebateActions>()(
  persist(
    (set) => ({
      ...initial,

  debateCreated: (debateId, canvasToBackend, initialCycles) =>
    set({
      debateId,
      canvasToBackend,
      cyclesByBackendId: initialCycles,
      eventLog: [],
    }),

  cycleMapped: (canvasCycleId, backendCycleId) =>
    set((state) => ({
      canvasToBackend: {
        ...state.canvasToBackend,
        [canvasCycleId]: backendCycleId,
      },
    })),

  cyclePopulated: (backendCycleId, cycle) =>
    set((state) => {
      const existing = state.cyclesByBackendId[backendCycleId]
      if (!existing) {
        return {
          cyclesByBackendId: {
            ...state.cyclesByBackendId,
            [backendCycleId]: cycle,
          },
        }
      }
      const seen = new Set(existing.turns.map((t) => t.turn_id))
      const mergedTurns = [
        ...existing.turns,
        ...cycle.turns.filter((t) => !seen.has(t.turn_id)),
      ]
      return {
        cyclesByBackendId: {
          ...state.cyclesByBackendId,
          [backendCycleId]: {
            ...cycle,
            turns: mergedTurns,
            synthesis: cycle.synthesis ?? existing.synthesis,
          },
        },
      }
    }),

  chipAdded: (canvasCycleId, agentId, steer) =>
    set((state) => {
      const cycle = state.chips[canvasCycleId] ?? {}
      const existing = cycle[agentId] ?? []
      return {
        chips: {
          ...state.chips,
          [canvasCycleId]: { ...cycle, [agentId]: [...existing, steer] },
        },
      }
    }),

  chipRemoved: (canvasCycleId, agentId, steerIndex) =>
    set((state) => {
      const cycle = state.chips[canvasCycleId] ?? {}
      const existing = cycle[agentId] ?? []
      const next = existing.filter((_, i) => i !== steerIndex)
      return {
        chips: {
          ...state.chips,
          [canvasCycleId]: { ...cycle, [agentId]: next },
        },
      }
    }),

  proposalSet: (canvasCycleId, agentId, turn) =>
    set((state) => {
      const cycle = state.proposals[canvasCycleId] ?? {}
      return {
        proposals: {
          ...state.proposals,
          [canvasCycleId]: { ...cycle, [agentId]: turn },
        },
      }
    }),

  eventReceived: (event) =>
    set((state) => {
      const log = [...state.eventLog, event]
      const cycleId = event.cycle_id
      if (cycleId == null) return { eventLog: log }
      const cycle = state.cyclesByBackendId[cycleId]
      if (!cycle) return { eventLog: log }

      if (event.event === "cycle.started") {
        return {
          eventLog: log,
          cyclesByBackendId: {
            ...state.cyclesByBackendId,
            [cycleId]: { ...cycle, status: "running" },
          },
        }
      }
      if (event.event === "cycle.awaiting") {
        return {
          eventLog: log,
          cyclesByBackendId: {
            ...state.cyclesByBackendId,
            [cycleId]: { ...cycle, status: "awaiting" },
          },
        }
      }
      if (event.event === "cycle.closed") {
        return {
          eventLog: log,
          cyclesByBackendId: {
            ...state.cyclesByBackendId,
            [cycleId]: { ...cycle, status: "complete" },
          },
        }
      }
      if (event.event === "turn.produced") {
        const raw = event.payload?.turn
        if (!raw) return { eventLog: log }
        const parsed = AgentTurnSchema.safeParse(raw)
        if (!parsed.success) return { eventLog: log }
        const incoming = parsed.data
        if (cycle.turns.some((t) => t.turn_id === incoming.turn_id)) {
          return { eventLog: log }
        }
        return {
          eventLog: log,
          cyclesByBackendId: {
            ...state.cyclesByBackendId,
            [cycleId]: { ...cycle, turns: [...cycle.turns, incoming] },
          },
        }
      }
      return { eventLog: log }
    }),

      reset: () => set({ ...initial }),
    }),
    {
      name: "hypo-debate",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        debateId: s.debateId,
        canvasToBackend: s.canvasToBackend,
        cyclesByBackendId: s.cyclesByBackendId,
        chips: s.chips,
        proposals: s.proposals,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return
        state.eventLog = []
      },
    },
  ),
)

export function useCycleChipCount(canvasCycleId: string | null): number {
  return useDebateStore((s) => {
    if (!canvasCycleId) return 0
    const cycle = s.chips[canvasCycleId]
    if (!cycle) return 0
    return Object.values(cycle).reduce((a, b) => a + b.length, 0)
  })
}

export function useSteeredAgentCount(canvasCycleId: string | null): number {
  return useDebateStore((s) => {
    if (!canvasCycleId) return 0
    const cycle = s.chips[canvasCycleId]
    if (!cycle) return 0
    return Object.values(cycle).filter((arr) => arr.length > 0).length
  })
}

export function useAgentChipCount(
  canvasCycleId: string | null,
  agentId: string | null,
): number {
  return useDebateStore((s) => {
    if (!canvasCycleId || !agentId) return 0
    return s.chips[canvasCycleId]?.[agentId]?.length ?? 0
  })
}

export function useAgentChips(
  canvasCycleId: string | null,
  agentId: string | null,
): Steer[] {
  return useDebateStore((s) => {
    if (!canvasCycleId || !agentId) return []
    return s.chips[canvasCycleId]?.[agentId] ?? []
  })
}

export function useProposal(
  canvasCycleId: string | null,
  agentId: string | null,
): AgentTurn | undefined {
  return useDebateStore((s) => {
    if (!canvasCycleId || !agentId) return undefined
    return s.proposals[canvasCycleId]?.[agentId]
  })
}

export function useCycleTurns(canvasCycleId: string | null): Cycle | null {
  return useDebateStore((s) => {
    if (!canvasCycleId) return null
    const backendId = s.canvasToBackend[canvasCycleId]
    if (!backendId) return null
    return s.cyclesByBackendId[backendId] ?? null
  })
}
