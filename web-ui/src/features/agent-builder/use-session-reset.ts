import { useChainStore } from "@/features/hypo-canvas/chain-store"
import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { useSelectionStore } from "@/features/hypo-canvas/selection-store"
import { useAgentBuilderStore } from "@/store/agent-builder"

export function useSessionReset() {
  const resetChain = useChainStore((s) => s.reset)
  const resetDebate = useDebateStore((s) => s.reset)
  const clearSelection = useSelectionStore((s) => s.nodeSelected)
  const clearAgentBuilder = useAgentBuilderStore(
    (s) => s.researchProblemCleared,
  )

  return () => {
    resetChain()
    resetDebate()
    clearSelection(null)
    clearAgentBuilder()
  }
}

export function useChainReset() {
  const resetChain = useChainStore((s) => s.reset)
  const resetDebate = useDebateStore((s) => s.reset)
  const clearSelection = useSelectionStore((s) => s.nodeSelected)

  return () => {
    resetChain()
    resetDebate()
    clearSelection(null)
  }
}
