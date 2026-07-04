"use client"

import { memo } from "react"
import type { Node, NodeProps } from "@xyflow/react"
import { Check, LoaderCircle, TriangleAlert } from "lucide-react"

import { ChainHandle } from "@/components/reactflow/handles/chain"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { useDebate } from "@/hooks/use-debate"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"
import { formatElapsed, useElapsed } from "@/features/hypo-canvas/use-elapsed"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"

type DebateData = Extract<CanvasNodeData, { kind: "debate" }>
type DebateNodeT = Node<DebateData, "debate">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function DebateNodeComponent({ selected }: NodeProps<DebateNodeT>) {
  const { data: debate } = useDebate()
  const debateStage = useAgentBuilderStore((s) => s.pipelineStages.debate)
  const debateError = useAgentBuilderStore((s) => s.stageErrors.debate)
  const elapsed = useElapsed("debate")
  const turns = debate?.cycle?.turns ?? []
  const turnCount = turns.length
  const citationCount = turns.reduce(
    (acc, t) => acc + (t.response.evidence?.length ?? 0),
    0,
  )
  const failed = debateStage === "failed"
  const isRunning =
    !failed && (debateStage === "running" || !debate?.cycle?.synthesis)
  const elapsedText = elapsed != null ? formatElapsed(elapsed) : null

  return (
    <>
      <ChainHandle position="top" />
      <div
        className={cn(
          "flex w-72 flex-col gap-1.5 rounded-2xl border bg-card p-3 transition-shadow duration-200 hover:shadow-md",
          "animate-in fade-in-0 zoom-in-95 duration-300",
          failed && "border-destructive/50",
          selected && "border-primary ring-2 ring-primary/25",
        )}
      >
        <div className="flex items-center justify-between">
          <span className={LABEL}>Debate</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {failed ? (
            <>
              <TriangleAlert className="size-4 shrink-0 text-destructive" />
              <span className="text-s text-destructive">
                {debateError ?? "Debate failed"}
              </span>
            </>
          ) : isRunning ? (
            <>
              <LoaderCircle className="size-4 animate-spin text-foreground" />
              <TextShimmer className="text-s">
                Running debate…{elapsedText ? ` ${elapsedText}` : ""}
              </TextShimmer>
            </>
          ) : (
            <>
              <Check className="size-4 text-muted-foreground" />
              <span className="text-s text-muted-foreground">
                {turnCount} turn{turnCount === 1 ? "" : "s"}
                {citationCount > 0 &&
                  ` · ${citationCount} citation${citationCount === 1 ? "" : "s"}`}
                {elapsedText ? ` · ${elapsedText}` : ""}
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
