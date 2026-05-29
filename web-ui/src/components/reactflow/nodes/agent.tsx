"use client"

import { memo } from "react"
import type { Node, NodeProps } from "@xyflow/react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { ChainHandle } from "@/components/reactflow/handles/chain"
import { cn } from "@/lib/utils"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"
import { useAgentColor } from "@/utils/agent-color"
import { humanizeEnum } from "@/utils/format"

type AgentData = Extract<CanvasNodeData, { kind: "agent" }>
type AgentNodeT = Node<AgentData, "agent">

const LABEL =
  "text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground"

function AgentNodeComponent({ data, selected }: NodeProps<AgentNodeT>) {
  const color = useAgentColor(data.clusterId)
  return (
    <>
      <ChainHandle position="top" />
      <div
        className={cn(
          "flex w-72 flex-col gap-1.5 rounded-2xl border border-l-4 bg-card p-3 transition-shadow duration-200 hover:shadow-md",
          color.accent,
          "animate-in fade-in-0 zoom-in-95 duration-300",
          selected && "border-primary ring-2 ring-primary/25",
        )}
      >
        <span className={LABEL}>Agent</span>
        <div className="flex min-w-0 items-center gap-2">
          <AgentAvatar
            clusterId={data.clusterId}
            name={data.name}
            className="size-7"
            fallbackClassName="text-[10px]"
          />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium">{data.name}</span>
            <span className="truncate font-mono text-[10px] uppercase text-muted-foreground">
              {humanizeEnum(data.reasoningStyle)}
            </span>
          </div>
        </div>
      </div>
      <ChainHandle position="bottom" />
    </>
  )
}

export const AgentNode = memo(AgentNodeComponent)
