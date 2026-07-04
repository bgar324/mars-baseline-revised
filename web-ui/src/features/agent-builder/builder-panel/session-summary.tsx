"use client"

import { useQuery } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PipelineStateSchema, type PipelineState } from "@/types/query"

const LABEL = "font-mono text-xs uppercase tracking-wide text-muted-foreground"

function totalTokens(state: PipelineState | undefined): number {
  if (!state) return 0
  let total = 0
  for (const stage of Object.values(state.stages)) {
    const usage = (stage as { usage?: { total_tokens?: unknown } }).usage
    if (typeof usage?.total_tokens === "number") total += usage.total_tokens
  }
  return total
}

function elapsedText(stageTimings: Record<string, { start: number; end: number | null }>) {
  const timings = Object.values(stageTimings)
  if (timings.length === 0) return "0s"
  const start = Math.min(...timings.map((t) => t.start))
  const end = timings.every((t) => t.end != null)
    ? Math.max(...timings.map((t) => t.end as number))
    : Date.now()
  const seconds = Math.max(0, Math.round((end - start) / 1000))
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

async function fetchState(queryId: string): Promise<PipelineState> {
  return fetcher(`/api/query/${queryId}`, PipelineStateSchema)
}

export function SessionSummary() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const pipelineStages = useAgentBuilderStore((s) => s.pipelineStages)
  const stageTimings = useAgentBuilderStore((s) => s.stageTimings)
  const hasRunning = Object.values(pipelineStages).some((s) => s === "running")
  const failed = Object.values(pipelineStages).some((s) => s === "failed")
  const completed = Object.values(pipelineStages).filter((s) => s === "complete")
    .length

  const { data } = useQuery({
    queryKey: ["query-state", queryId],
    queryFn: () => fetchState(queryId!),
    enabled: !!queryId,
    refetchInterval: hasRunning ? 5000 : false,
    staleTime: hasRunning ? 0 : 30_000,
  })

  if (!queryId) return null

  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2">
      <div className="mb-1 flex items-center justify-between">
        <span className={LABEL}>Session</span>
        <span className={LABEL}>
          {failed ? "failed" : hasRunning ? "running" : "active"}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <span>{completed}/5 stages</span>
        <span>{elapsedText(stageTimings)}</span>
        <span>{totalTokens(data).toLocaleString()} tokens</span>
      </div>
    </div>
  )
}
