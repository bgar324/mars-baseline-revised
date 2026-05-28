import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { PersonaAgent } from "@/types/persona"

const TEAM_MAX = 3

export type PersonaPatch = Partial<
  Pick<
    PersonaAgent,
    | "name"
    | "framing"
    | "background"
    | "reasoning_style"
    | "evaluation_lens"
    | "instructions"
    | "constraints"
  >
>

type AgentBuilderState = {
  draft: string
  committed: string | null
  queryId: string | null
  team: PersonaAgent[]
  selectedClusterId: number | null
  personaEdits: Record<number, PersonaPatch>
}

type AgentBuilderActions = {
  researchProblemDraftChanged: (text: string) => void
  researchProblemCommitted: (text: string, queryId: string) => void
  researchProblemCleared: () => void
  agentSelected: (clusterId: number | null) => void
  teamMemberAdded: (persona: PersonaAgent) => void
  teamMemberRemoved: (clusterId: number) => void
  personaEdited: (clusterId: number, patch: PersonaPatch) => void
}

export const TEAM_SIZE_MAX = TEAM_MAX

export const useAgentBuilderStore = create<
  AgentBuilderState & AgentBuilderActions
>()(
  persist(
    (set) => ({
      draft: "",
      committed: null,
      queryId: null,
      team: [],
      selectedClusterId: null,
      personaEdits: {},

      researchProblemDraftChanged: (text) => set({ draft: text }),

      researchProblemCommitted: (text, queryId) =>
        set({ draft: text, committed: text, queryId }),

      researchProblemCleared: () =>
        set({
          draft: "",
          committed: null,
          queryId: null,
          team: [],
          selectedClusterId: null,
          personaEdits: {},
        }),

      agentSelected: (clusterId) => set({ selectedClusterId: clusterId }),

      teamMemberAdded: (persona) =>
        set((state) => {
          if (state.team.length >= TEAM_MAX) return state
          if (state.team.some((p) => p.cluster_id === persona.cluster_id))
            return state
          return { team: [...state.team, persona] }
        }),

      teamMemberRemoved: (clusterId) =>
        set((state) => ({
          team: state.team.filter((p) => p.cluster_id !== clusterId),
        })),

      personaEdited: (clusterId, patch) =>
        set((state) => ({
          personaEdits: {
            ...state.personaEdits,
            [clusterId]: { ...state.personaEdits[clusterId], ...patch },
          },
        })),
    }),
    {
      name: "agent-builder",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        draft: s.draft,
        committed: s.committed,
        queryId: s.queryId,
        team: s.team,
        selectedClusterId: s.selectedClusterId,
        personaEdits: s.personaEdits,
      }),
      version: 1,
    },
  ),
)
