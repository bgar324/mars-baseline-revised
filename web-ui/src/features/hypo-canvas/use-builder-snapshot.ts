"use client"

import { useMemo } from "react"

import { useAgentBuilderStore } from "@/store/agent-builder"

import type { BuilderSnapshot } from "./types"

export function useBuilderSnapshot(): BuilderSnapshot {
  const committed = useAgentBuilderStore((s) => s.committed)
  const focalClaim = useAgentBuilderStore((s) => s.focalClaim)
  const pipelineStages = useAgentBuilderStore((s) => s.pipelineStages)
  const team = useAgentBuilderStore((s) => s.team)
  return useMemo(
    () => ({
      query: committed,
      focalClaim,
      pipelineStages,
      team,
    }),
    [committed, focalClaim, pipelineStages, team],
  )
}
