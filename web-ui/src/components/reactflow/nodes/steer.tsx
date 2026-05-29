"use client"

import { memo } from "react"
import type { Node, NodeProps } from "@xyflow/react"

import { ChainHandle } from "@/components/reactflow/handles/chain"
import { cn } from "@/lib/utils"
import { useSteeredAgentCount } from "@/features/hypo-canvas/debate-store"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"

type SteerData = Extract<CanvasNodeData, { kind: "steer" }>
type SteerNodeT = Node<SteerData, "steer">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function SteerNodeComponent({ data, selected }: NodeProps<SteerNodeT>) {
  const canvasCycleId = `s${data.n}`
  const steeredCount = useSteeredAgentCount(canvasCycleId)
  const variant = data.n === 0 ? "pre-debate" : "post-debate"
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
          <span className={LABEL}>Steer</span>
          <span className={LABEL}>
            cycle {data.n} · {variant}
          </span>
        </div>
        <p className="text-sm">3 agents · {steeredCount} of 3 steered</p>
      </div>
      <ChainHandle position="bottom" />
    </>
  )
}

export const SteerNode = memo(SteerNodeComponent)
