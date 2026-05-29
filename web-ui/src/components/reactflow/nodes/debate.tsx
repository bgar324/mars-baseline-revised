"use client"

import { memo } from "react"
import type { Node, NodeProps } from "@xyflow/react"
import { Check, LoaderCircle } from "lucide-react"

import { TextShimmer } from "@/components/ui/text-shimmer"
import { ChainHandle } from "@/components/reactflow/handles/chain"
import { cn } from "@/lib/utils"
import { useCycleTurns } from "@/features/hypo-canvas/debate-store"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"

type DebateData = Extract<CanvasNodeData, { kind: "debate" }>
type DebateNodeT = Node<DebateData, "debate">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function DebateNodeComponent({ data, selected }: NodeProps<DebateNodeT>) {
  const canvasCycleId = `d${data.n}`
  const cycle = useCycleTurns(canvasCycleId)
  const isRunning = data.status === "running" || !cycle
  const turnCount = cycle?.turns.length ?? 0
  const citationCount =
    cycle?.turns.reduce((acc, t) => acc + (t.evidence?.length ?? 0), 0) ?? 0
  return (
    <>
      <ChainHandle position="top" />
      <div
        className={cn(
          "flex w-72 flex-col gap-1.5 rounded-2xl border bg-card p-3 transition-shadow duration-200 hover:shadow-md",
          "animate-in fade-in-0 zoom-in-95 duration-300",
          selected && "border-primary ring-2 ring-primary/25",
        )}
      >
        <div className="flex items-center justify-between">
          <span className={LABEL}>Debate</span>
          <span className={LABEL}>cycle {data.n}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {isRunning ? (
            <>
              <LoaderCircle className="size-4 animate-spin text-foreground" />
              <TextShimmer className="text-s">Running debate…</TextShimmer>
            </>
          ) : (
            <>
              <Check className="size-4 text-muted-foreground" />
              <span className="text-s text-muted-foreground">
                {turnCount} turn{turnCount === 1 ? "" : "s"}
                {citationCount > 0 && ` · ${citationCount} citation${citationCount === 1 ? "" : "s"}`}
              </span>
            </>
          )}
        </div>
      </div>
      <ChainHandle position="bottom" />
    </>
  )
}

export const DebateNode = memo(DebateNodeComponent)
