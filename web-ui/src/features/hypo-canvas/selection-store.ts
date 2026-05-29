import { create } from "zustand"

type SelectionState = {
  selectedNodeId: string | null
  secondaryAgentId: string | null
}

type SelectionActions = {
  nodeSelected: (id: string | null) => void
  secondaryAgentSelected: (id: string | null) => void
}

export const useSelectionStore = create<SelectionState & SelectionActions>(
  (set) => ({
    selectedNodeId: null,
    secondaryAgentId: null,

    nodeSelected: (id) =>
      set(() => {
        if (id == null) {
          return { selectedNodeId: null, secondaryAgentId: null }
        }
        return { selectedNodeId: id }
      }),

    secondaryAgentSelected: (id) => set({ secondaryAgentId: id }),
  }),
)
