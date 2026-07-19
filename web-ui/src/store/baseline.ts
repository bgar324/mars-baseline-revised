import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"

type BaselineState = {
  activeAgentIds: number[]
  target: number | null
  startedAt: string | null
  testMode: boolean
  manualPersonas: PersonaAgent[]
  manualPapers: Paper[]
}

type BaselineActions = {
  activeAgentsSet: (ids: number[]) => void
  targetSet: (target: number | null) => void
  sessionStarted: (testMode?: boolean) => void
  manualPersonaAdded: (persona: PersonaAgent) => void
  manualPersonaEdited: (
    clusterId: number,
    patch: Partial<PersonaAgent>,
  ) => void
  manualPersonaRemoved: (clusterId: number) => void
  manualPapersAdded: (papers: Paper[]) => void
  reset: () => void
}

const initialState: BaselineState = {
  activeAgentIds: [],
  target: null,
  startedAt: null,
  testMode: false,
  manualPersonas: [],
  manualPapers: [],
}

export const useBaselineStore = create<BaselineState & BaselineActions>()(
  persist(
    (set) => ({
      ...initialState,
      activeAgentsSet: (activeAgentIds) => set({ activeAgentIds }),
      targetSet: (target) => set({ target }),
      sessionStarted: (testMode = false) =>
        set({ startedAt: new Date().toISOString(), testMode }),
      manualPersonaAdded: (persona) =>
        set((state) => ({
          manualPersonas: [...state.manualPersonas, persona],
        })),
      manualPersonaEdited: (clusterId, patch) =>
        set((state) => ({
          manualPersonas: state.manualPersonas.map((persona) =>
            persona.cluster_id === clusterId
              ? { ...persona, ...patch }
              : persona,
          ),
        })),
      manualPersonaRemoved: (clusterId) =>
        set((state) => ({
          manualPersonas: state.manualPersonas.filter(
            (persona) => persona.cluster_id !== clusterId,
          ),
          activeAgentIds: state.activeAgentIds.filter((id) => id !== clusterId),
          target: state.target === clusterId ? null : state.target,
        })),
      manualPapersAdded: (papers) =>
        set((state) => ({
          manualPapers: [
            ...new Map(
              [...state.manualPapers, ...papers].map((paper) => [
                paper.id,
                paper,
              ]),
            ).values(),
          ],
        })),
      reset: () => set(initialState),
    }),
    {
      name: "baseline-workspace",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activeAgentIds: state.activeAgentIds,
        target: state.target,
        startedAt: state.startedAt,
        testMode: state.testMode,
        manualPersonas: state.manualPersonas,
        manualPapers: state.manualPapers,
      }),
    },
  ),
)
