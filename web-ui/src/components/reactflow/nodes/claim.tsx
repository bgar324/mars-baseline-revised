"use client"

import { memo } from "react"
import type { Node, NodeProps } from "@xyflow/react"

import { ChainHandle } from "@/components/reactflow/handles/chain"
import { cn } from "@/lib/utils"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"

type ClaimData = Extract<CanvasNodeData, { kind: "claim" }>
type ClaimNodeT = Node<ClaimData, "claim">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function ClaimNodeComponent({ data, selected }: NodeProps<ClaimNodeT>) {
  return (
    <>
      <ChainHandle position="top" />
      <div
        className={cn(
          "flex w-72 flex-col gap-1 rounded-2xl border bg-card p-3 transition-shadow duration-200 hover:shadow-md",
          "animate-in fade-in-0 zoom-in-95 duration-300",
          selected && "border-primary ring-2 ring-primary/25",
        )}
      >
        <span className={LABEL}>Focal Claim</span>
        {data.focalClaim ? (
          <p className="line-clamp-3 text-sm font-medium leading-snug">
            &ldquo;{data.focalClaim}&rdquo;
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            No focal claim yet.
          </p>
        )}
      </div>
      <ChainHandle position="bottom" />
    </>
  )
}

export const ClaimNode = memo(ClaimNodeComponent)
