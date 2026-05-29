"use client"

import { useState } from "react"
import { Check } from "lucide-react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"
import { AGENT_PALETTE, autoAgentColorIndex } from "@/utils/agent-color"

const FIELD_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

export function ContextPanelHeader({ persona }: { persona: PersonaAgent }) {
  const edit = useAgentBuilderStore((s) => s.personaEdited)
  const setColor = useAgentBuilderStore((s) => s.agentColorSet)
  const override = useAgentBuilderStore((s) => s.agentColors[persona.cluster_id])
  const [name, setName] = useState(persona.name)
  const [trackedId, setTrackedId] = useState(persona.cluster_id)

  if (trackedId !== persona.cluster_id) {
    setTrackedId(persona.cluster_id)
    setName(persona.name)
  }

  const commit = () => {
    const trimmed = name.trim()
    if (!trimmed || trimmed === persona.name) {
      setName(persona.name)
      return
    }
    edit(persona.cluster_id, { name: trimmed })
  }

  const selected = override ?? autoAgentColorIndex(persona.cluster_id)

  return (
    <div className="flex items-start gap-3 border-b p-4">
      <AgentAvatar
        clusterId={persona.cluster_id}
        name={persona.name}
        className="size-10"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div className="flex flex-col gap-1">
          <span className={FIELD_LABEL}>Display name</span>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                ;(e.target as HTMLInputElement).blur()
              }
              if (e.key === "Escape") {
                setName(persona.name)
                ;(e.target as HTMLInputElement).blur()
              }
            }}
            className="h-8 text-s font-medium"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            {AGENT_PALETTE.map((c, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Color ${i + 1}`}
                aria-pressed={i === selected}
                onClick={() => setColor(persona.cluster_id, i)}
                className={cn(
                  "flex size-6 items-center justify-center rounded-full transition-transform hover:scale-110",
                  c.swatch,
                  i === selected &&
                    "ring-2 ring-ring ring-offset-1 ring-offset-background",
                )}
              >
                {i === selected && <Check className="size-3.5 text-white" />}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
