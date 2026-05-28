"use client"

import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAgentBuilderStore } from "@/store/agent-builder"

export function AgentBuilderHeader() {
  const committed = useAgentBuilderStore((s) => s.committed)
  const teamSize = useAgentBuilderStore((s) => s.team.length)

  const canCreate = !!committed && teamSize >= 1

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b px-4">
      <h1 className="font-sans text-sm uppercase tracking-wide">
        Agent Builder
      </h1>
      <Button variant="outline" size="sm" disabled={!canCreate}>
        Create
        <Plus />
      </Button>
    </header>
  )
}
