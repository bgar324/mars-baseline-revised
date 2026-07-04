"use client"

import { memo, useEffect, useState } from "react"
import type { Node, NodeProps } from "@xyflow/react"
import { Check, LoaderCircle, TriangleAlert } from "lucide-react"

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/ui/chain-of-thought"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { ChainHandle } from "@/components/reactflow/handles/chain"
import { formatElapsed } from "@/features/hypo-canvas/use-elapsed"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type {
  CanvasNodeData,
  ResearchStage,
} from "@/features/hypo-canvas/types"

type ResearchData = Extract<CanvasNodeData, { kind: "research" }>
type ResearchNodeT = Node<ResearchData, "research">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function ResearchNodeComponent({ data, selected }: NodeProps<ResearchNodeT>) {
  const stages = data.stages ?? []
  const visible = stages.filter(
    (s) =>
      s.status === "done" || s.status === "running" || s.status === "failed",
  )
  const doneCount = stages.filter((s) => s.status === "done").length
  const hasRunning = stages.some((s) => s.status === "running")
  const hasFailed = stages.some((s) => s.status === "failed")

  const stageTimings = useAgentBuilderStore((s) => s.stageTimings)
  const [now, setNow] = useState(0)

  useEffect(() => {
    if (!hasRunning) return
    const id = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(id)
  }, [hasRunning])

  const stageKeys = new Set<string>(stages.map((s) => s.key))
  const times = Object.entries(stageTimings)
    .filter(([k]) => stageKeys.has(k))
    .map(([, t]) => t)
  const start = times.length ? Math.min(...times.map((t) => t.start)) : null
  const allEnded =
    times.length > 0 && times.every((t) => t.end !== null)
  const end = allEnded
    ? Math.max(...times.map((t) => t.end as number))
    : null
  const total = start !== null ? (end ?? now) - start : null

  return (
    <>
      <div
        className={cn(
          "flex w-[28rem] flex-col gap-2 rounded-2xl border bg-card p-3 transition-shadow duration-200 hover:shadow-md",
          "animate-in fade-in-0 zoom-in-95 duration-300",
          selected && "border-primary ring-2 ring-primary/25",
        )}
      >
        <div className="flex flex-col gap-1">
          <span className={LABEL}>Research Problem</span>
          {data.query ? (
            <p className="text-s leading-snug">{data.query}</p>
          ) : (
            <p className="text-s text-muted-foreground">
              No research problem yet.
            </p>
          )}
        </div>

        {visible.length > 0 && (
          <ChainOfThought>
            <ChainOfThoughtStep defaultOpen>
              <ChainOfThoughtTrigger>
                <span className="inline-flex items-center gap-1 text-s text-muted-foreground">
                  <span className={cn(hasFailed && "text-destructive")}>
                    Pipeline · {doneCount} of {stages.length} ·{" "}
                    {hasFailed
                      ? `Failed${total !== null ? ` after ${formatElapsed(total)}` : ""}`
                      : doneCount === stages.length
                        ? `Completed${total !== null ? ` in ${formatElapsed(total)}` : ""}`
                        : `Running… ${total !== null ? formatElapsed(total) : "0s"}`}
                  </span>
                  {hasFailed ? (
                    <TriangleAlert className="size-3.5 shrink-0 text-destructive" />
                  ) : (
                    doneCount === stages.length && (
                      <Check className="size-3.5 shrink-0" />
                    )
                  )}
                </span>
              </ChainOfThoughtTrigger>
              <ChainOfThoughtContent>
                {visible.map((stage) => (
                  <StageRow key={stage.name} stage={stage} />
                ))}
              </ChainOfThoughtContent>
            </ChainOfThoughtStep>
          </ChainOfThought>
        )}
      </div>
      <ChainHandle position="bottom" />
    </>
  )
}

function StageRow({ stage }: { stage: ResearchStage }) {
  const isDone = stage.status === "done"
  const isFailed = stage.status === "failed"
  return (
    <div className="animate-in fade-in-0 duration-500 flex flex-col gap-0.5">
      <div className="flex items-center gap-2">
        {isFailed ? (
          <TriangleAlert className="size-4 shrink-0 text-destructive" />
        ) : isDone ? (
          <Check className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <LoaderCircle className="size-4 shrink-0 animate-spin text-foreground" />
        )}
        {isFailed ? (
          <span className="text-s text-destructive">{stage.name}</span>
        ) : isDone ? (
          <span className="text-s text-muted-foreground line-through">
            {stage.name}
          </span>
        ) : (
          <TextShimmer className="text-s">{stage.name}</TextShimmer>
        )}
      </div>
      {isFailed && stage.error ? (
        <span className="ml-6 text-xs text-destructive">{stage.error}</span>
      ) : (
        stage.description &&
        !isDone && (
          <span className="ml-6 text-xs text-muted-foreground">
            {stage.description}
          </span>
        )
      )}
    </div>
  )
}

export const ResearchNode = memo(ResearchNodeComponent)
