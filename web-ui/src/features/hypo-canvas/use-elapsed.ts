"use client"

import { useEffect, useState } from "react"

import { useAgentBuilderStore } from "@/store/agent-builder"
import type { StageName } from "@/types/query"

export function formatElapsed(ms: number): string {
  return `${Math.max(0, Math.floor(ms / 1000))}s`
}

export function useElapsed(stage: StageName): number | null {
  const timing = useAgentBuilderStore((s) => s.stageTimings[stage])
  const running = useAgentBuilderStore((s) => s.pipelineStages[stage]) === "running"
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(id)
  }, [running])

  if (!timing) return null
  return (timing.end ?? now) - timing.start
}
