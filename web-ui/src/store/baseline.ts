import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

type BaselineState = {
  activeAgentIds: number[]
  target: "all" | number
  startedAt: string | null
  testMode: boolean
}

type BaselineActions = {
  activeAgentsSet: (ids: number[]) => void
  targetSet: (target: "all" | number) => void
  sessionStarted: (testMode?: boolean) => void
  reset: () => void
}

const initialState: BaselineState = {
  activeAgentIds: [],
  target: "all",
  startedAt: null,
  testMode: false,
}

export const useBaselineStore = create<BaselineState & BaselineActions>()(
  persist(
    (set) => ({
      ...initialState,
      activeAgentsSet: (activeAgentIds) => set({ activeAgentIds }),
      targetSet: (target) => set({ target }),
      sessionStarted: (testMode = false) =>
        set({ startedAt: new Date().toISOString(), testMode }),
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
      }),
    },
  ),
)
