import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { PersonaAgent } from "@/types/persona"
import type { StageName, StageStatus } from "@/types/query"

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
  focalClaim: string | null
  pipelineStages: Partial<Record<StageName, StageStatus>>
  personas: PersonaAgent[]
  team: PersonaAgent[]
  selectedClusterId: number | null
  personaEdits: Record<number, PersonaPatch>
}

type AgentBuilderActions = {
  researchProblemDraftChanged: (text: string) => void
  researchProblemCommitted: (text: string, queryId: string) => void
  researchProblemCleared: () => void
  focalClaimSet: (claim: string | null) => void
  pipelineStageSet: (stage: StageName, status: StageStatus) => void
  pipelineStagesReset: () => void
  personasSet: (personas: PersonaAgent[]) => void
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
      focalClaim: null,
      pipelineStages: {},
      personas: [],
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
          focalClaim: null,
          pipelineStages: {},
          personas: [],
          team: [],
          selectedClusterId: null,
          personaEdits: {},
        }),

      personasSet: (personas) => set({ personas }),

      focalClaimSet: (claim) => set({ focalClaim: claim }),

      pipelineStageSet: (stage, status) =>
        set((state) => ({
          pipelineStages: { ...state.pipelineStages, [stage]: status },
        })),

      pipelineStagesReset: () => set({ pipelineStages: {} }),

      agentSelected: (clusterId) => set({ selectedClusterId: clusterId }),

      teamMemberAdded: (persona) =>
        set((state) => {
          if (state.team.length >= TEAM_MAX) return state
          if (state.team.some((p) => p.cluster_id === persona.cluster_id))
            return state
          return {
            team: [...state.team, persona],
            selectedClusterId:
              state.team.length === 0
                ? persona.cluster_id
                : state.selectedClusterId,
          }
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
        focalClaim: s.focalClaim,
        pipelineStages: s.pipelineStages,
        personas: s.personas,
        team: s.team,
        selectedClusterId: s.selectedClusterId,
        personaEdits: s.personaEdits,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return
        const sanitized: typeof state.pipelineStages = {}
        for (const [k, v] of Object.entries(state.pipelineStages ?? {})) {
          sanitized[k as keyof typeof sanitized] =
            v === "running" ? "pending" : v
        }
        state.pipelineStages = sanitized
      },
    },
  ),
)
