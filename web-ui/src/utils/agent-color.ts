"use client"

import { useAgentBuilderStore } from "@/store/agent-builder"

export type AgentColorClasses = {
  solid: string
  tint: string
  swatch: string
  accent: string
}

export const AGENT_PALETTE: AgentColorClasses[] = [
  { solid: "bg-agent-1 text-white", tint: "bg-agent-1/12 text-agent-1", swatch: "bg-agent-1", accent: "border-l-agent-1" },
  { solid: "bg-agent-2 text-white", tint: "bg-agent-2/12 text-agent-2", swatch: "bg-agent-2", accent: "border-l-agent-2" },
  { solid: "bg-agent-3 text-white", tint: "bg-agent-3/12 text-agent-3", swatch: "bg-agent-3", accent: "border-l-agent-3" },
  { solid: "bg-agent-4 text-white", tint: "bg-agent-4/12 text-agent-4", swatch: "bg-agent-4", accent: "border-l-agent-4" },
  { solid: "bg-agent-5 text-white", tint: "bg-agent-5/12 text-agent-5", swatch: "bg-agent-5", accent: "border-l-agent-5" },
  { solid: "bg-agent-6 text-white", tint: "bg-agent-6/12 text-agent-6", swatch: "bg-agent-6", accent: "border-l-agent-6" },
  { solid: "bg-agent-7 text-white", tint: "bg-agent-7/12 text-agent-7", swatch: "bg-agent-7", accent: "border-l-agent-7" },
  { solid: "bg-agent-8 text-white", tint: "bg-agent-8/12 text-agent-8", swatch: "bg-agent-8", accent: "border-l-agent-8" },
  { solid: "bg-agent-9 text-white", tint: "bg-agent-9/12 text-agent-9", swatch: "bg-agent-9", accent: "border-l-agent-9" },
  { solid: "bg-agent-10 text-white", tint: "bg-agent-10/12 text-agent-10", swatch: "bg-agent-10", accent: "border-l-agent-10" },
]

export const AGENT_COLOR_COUNT = AGENT_PALETTE.length

export function autoAgentColorIndex(clusterId: number): number {
  return ((clusterId % AGENT_COLOR_COUNT) + AGENT_COLOR_COUNT) % AGENT_COLOR_COUNT
}

export function agentColorClasses(index: number): AgentColorClasses {
  return AGENT_PALETTE[autoAgentColorIndex(index)]
}

export function useAgentColor(clusterId: number): AgentColorClasses {
  const override = useAgentBuilderStore((s) => s.agentColors[clusterId])
  return agentColorClasses(override ?? clusterId)
}

export function useAgentColors(): Record<number, number> {
  return useAgentBuilderStore((s) => s.agentColors)
}
