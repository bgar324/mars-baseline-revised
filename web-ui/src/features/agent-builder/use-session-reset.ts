import { useSelectionStore } from "@/features/hypo-canvas/selection-store"
import { useAgentBuilderStore } from "@/store/agent-builder"

export function useSessionReset() {
  const clearSelection = useSelectionStore((s) => s.nodeSelected)
  const clearAgentBuilder = useAgentBuilderStore(
    (s) => s.researchProblemCleared,
  )

  return () => {
    clearSelection(null)
    clearAgentBuilder()
  }
}
