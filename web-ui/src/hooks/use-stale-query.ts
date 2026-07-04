"use client"

import { isStaleQueryError } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"

export function clearStaleQuery(error: unknown): boolean {
  const stale =
    isStaleQueryError(error) ||
    (typeof error === "object" &&
      error !== null &&
      "status" in error &&
      (error as { status?: unknown }).status === 404)
  if (!stale) return false
  useAgentBuilderStore.getState().researchProblemCleared()
  return true
}
