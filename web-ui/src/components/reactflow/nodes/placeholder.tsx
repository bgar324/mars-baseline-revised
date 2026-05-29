"use client"

import { memo } from "react"
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react"
import { Plus } from "lucide-react"

import { cn } from "@/lib/utils"
import type { CanvasNodeData } from "@/features/hypo-canvas/types"

type PlaceholderData = Extract<CanvasNodeData, { kind: "placeholder" }> & {
  onActivate?: () => void
}
type PlaceholderNodeT = Node<PlaceholderData, "placeholder">

const HIDDEN_HANDLE = { visibility: "hidden" as const }

function PlaceholderNodeComponent({ data }: NodeProps<PlaceholderNodeT>) {
  if (data.nextKind === "agent-slot") {
    return <AgentSlotPlaceholder />
  }
  return <CyclePlaceholder data={data} />
}

function AgentSlotPlaceholder() {
  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={false}
        style={HIDDEN_HANDLE}
      />
      <div
        className={cn(
          "flex h-14 w-44 items-center justify-center rounded-2xl border-2 border-dashed border-muted-foreground/30 bg-muted/30 text-muted-foreground",
          "transition-colors duration-200",
          "animate-in fade-in-0 zoom-in-95 duration-300",
        )}
      >
        <Plus className="size-5" aria-hidden />
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={false}
        style={HIDDEN_HANDLE}
      />
    </>
  )
}

function CyclePlaceholder({ data }: { data: PlaceholderData }) {
  const disabled = data.disabled
  const title = `${data.nextKind === "steer" ? "Steer" : "Debate"} · cycle ${data.n}`
  const body = disabled ? (data.blockedReason ?? "Locked") : "Click to start"
  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={false}
        style={HIDDEN_HANDLE}
      />
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onClick={() => !disabled && data.onActivate?.()}
        onKeyDown={(e) => {
          if (disabled) return
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            data.onActivate?.()
          }
        }}
        className={cn(
          "flex w-72 flex-col gap-1 rounded-2xl border border-dashed bg-card/60 p-3",
          "text-muted-foreground transition-colors",
          "animate-in fade-in-0 zoom-in-95 duration-300",
          !disabled &&
            "cursor-pointer hover:border-primary hover:bg-card hover:text-foreground",
          disabled && "opacity-50",
        )}
      >
        <span className="flex items-center gap-1.5 text-sm font-medium">
          <span aria-hidden className="text-base leading-none">
            +
          </span>
          {title}
        </span>
        <span className="text-xs">{body}</span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={false}
        style={HIDDEN_HANDLE}
      />
    </>
  )
}

export const PlaceholderNode = memo(PlaceholderNodeComponent)
