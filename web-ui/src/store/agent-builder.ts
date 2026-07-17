import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { PersonaAgent } from "@/types/persona"
import type { StageName, StageStatus } from "@/types/query"

export type RunMode = "auto" | "manual"
export type StudyCondition = "mars" | "baseline"

export type PersonaPatch = Partial<
  Pick<
    PersonaAgent,
    | "name"
    | "role"
    | "perspective"
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
  mode: RunMode
  studyCondition: StudyCondition
  focalClaim: string | null
  pipelineStages: Partial<Record<StageName, StageStatus>>
  pipelineSteps: Record<string, StageStatus>
  stageErrors: Partial<Record<StageName, string>>
  personas: PersonaAgent[]
  selectedClusterId: number | null
  personaEdits: Record<number, PersonaPatch>
  agentColors: Record<number, number>
  stageTimings: Record<string, { start: number; end: number | null }>
  /** Agents mid-turn in the live debate, keyed by agent_id → phase label. */
  thinkingAgents: Record<string, string>
}

type AgentBuilderActions = {
  researchProblemDraftChanged: (text: string) => void
  researchProblemCommitted: (
    text: string,
    queryId: string,
    condition?: StudyCondition,
  ) => void
  researchProblemCleared: () => void
  modeSet: (mode: RunMode) => void
  studyConditionSet: (condition: StudyCondition) => void
  focalClaimSet: (claim: string | null) => void
  pipelineStageSet: (
    stage: StageName,
    status: StageStatus,
    error?: string | null,
  ) => void
  pipelineStagesReset: () => void
  pipelineStepSet: (step: string, status: StageStatus) => void
  personasSet: (personas: PersonaAgent[]) => void
  agentSelected: (clusterId: number | null) => void
  personaEdited: (clusterId: number, patch: PersonaPatch) => void
  agentColorSet: (clusterId: number, index: number) => void
  agentThinkingStarted: (agentId: string, phase: string) => void
  agentTurnLanded: (agentId: string) => void
  debateActivityCleared: () => void
}

export const useAgentBuilderStore = create<
  AgentBuilderState & AgentBuilderActions
>()(
  persist(
    (set) => ({
      draft: "",
      committed: null,
      queryId: null,
      mode: "auto",
      studyCondition: "mars",
      focalClaim: null,
      pipelineStages: {},
      pipelineSteps: {},
      stageErrors: {},
      personas: [],
      selectedClusterId: null,
      personaEdits: {},
      agentColors: {},
      stageTimings: {},
      thinkingAgents: {},

      researchProblemDraftChanged: (text) => set({ draft: text }),

      researchProblemCommitted: (text, queryId, studyCondition = "mars") =>
        set({ draft: text, committed: text, queryId, studyCondition }),

      researchProblemCleared: () =>
        set({
          draft: "",
          committed: null,
          queryId: null,
          studyCondition: "mars",
          focalClaim: null,
          pipelineStages: {},
          pipelineSteps: {},
          stageErrors: {},
          personas: [],
          selectedClusterId: null,
          personaEdits: {},
          agentColors: {},
          stageTimings: {},
          thinkingAgents: {},
        }),

      personasSet: (personas) => set({ personas }),

      modeSet: (mode) => set({ mode }),

      studyConditionSet: (studyCondition) => set({ studyCondition }),

      focalClaimSet: (claim) => set({ focalClaim: claim }),

      pipelineStageSet: (stage, status, error) =>
        set((state) => {
          const timings = { ...state.stageTimings }
          if (status === "running") {
            timings[stage] = { start: Date.now(), end: null }
          } else if (
            status === "complete" ||
            status === "failed" ||
            status === "skipped"
          ) {
            const prev = timings[stage]
            timings[stage] = {
              start: prev?.start ?? Date.now(),
              end: Date.now(),
            }
          }
          const stageErrors = { ...state.stageErrors }
          if (error) stageErrors[stage] = error
          else delete stageErrors[stage]
          return {
            pipelineStages: { ...state.pipelineStages, [stage]: status },
            stageErrors,
            stageTimings: timings,
          }
        }),

      pipelineStagesReset: () =>
        set({
          pipelineStages: {},
          pipelineSteps: {},
          stageErrors: {},
          stageTimings: {},
          thinkingAgents: {},
        }),

      pipelineStepSet: (step, status) =>
        set((state) => ({
          pipelineSteps: { ...state.pipelineSteps, [step]: status },
        })),

      agentSelected: (clusterId) => set({ selectedClusterId: clusterId }),

      personaEdited: (clusterId, patch) =>
        set((state) => ({
          personaEdits: {
            ...state.personaEdits,
            [clusterId]: { ...state.personaEdits[clusterId], ...patch },
          },
        })),

      agentColorSet: (clusterId, index) =>
        set((state) => ({
          agentColors: { ...state.agentColors, [clusterId]: index },
        })),

      agentThinkingStarted: (agentId, phase) =>
        set((state) => ({
          thinkingAgents: { ...state.thinkingAgents, [agentId]: phase },
        })),

      agentTurnLanded: (agentId) =>
        set((state) => {
          if (!(agentId in state.thinkingAgents)) return state
          const thinkingAgents = { ...state.thinkingAgents }
          delete thinkingAgents[agentId]
          return { thinkingAgents }
        }),

      debateActivityCleared: () => set({ thinkingAgents: {} }),
    }),
    {
      name: "agent-builder",
      version: 2,
      storage: createJSONStorage(() => localStorage),
      migrate: (persisted) => ({
        ...(persisted as Partial<AgentBuilderState>),
        studyCondition:
          (persisted as Partial<AgentBuilderState>).studyCondition ?? "mars",
      }),
      partialize: (s) => ({
        draft: s.draft,
        committed: s.committed,
        queryId: s.queryId,
        mode: s.mode,
        studyCondition: s.studyCondition,
        focalClaim: s.focalClaim,
        pipelineStages: s.pipelineStages,
        personas: s.personas,
        selectedClusterId: s.selectedClusterId,
        personaEdits: s.personaEdits,
        agentColors: s.agentColors,
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
