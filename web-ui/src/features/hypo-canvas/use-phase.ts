import { useChainStore } from "./chain-store"

export type CanvasPhase = "builder" | "workflow"

export function usePhase(): CanvasPhase {
  const hasCycle = useChainStore((s) => s.cycles.length > 0)
  return hasCycle ? "workflow" : "builder"
}
