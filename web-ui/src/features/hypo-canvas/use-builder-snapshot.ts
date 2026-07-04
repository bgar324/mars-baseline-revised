"use client"

import { useMemo } from "react"

import { useAgentBuilderStore } from "@/store/agent-builder"

import type { BuilderSnapshot } from "./types"

export function useBuilderSnapshot(): BuilderSnapshot {
  const committed = useAgentBuilderStore((s) => s.committed)
  const focalClaim = useAgentBuilderStore((s) => s.focalClaim)
  const pipelineStages = useAgentBuilderStore((s) => s.pipelineStages)
  const stageErrors = useAgentBuilderStore((s) => s.stageErrors)
  const personas = useAgentBuilderStore((s) => s.personas)
  return useMemo(
    () => ({
      query: committed,
      focalClaim,
      pipelineStages,
      stageErrors,
      personas,
    }),
    [committed, focalClaim, pipelineStages, stageErrors, personas],
  )
}
