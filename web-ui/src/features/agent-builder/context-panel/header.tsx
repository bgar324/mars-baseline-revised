"use client"

import { useEffect, useState } from "react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Input } from "@/components/ui/input"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"
import { initials } from "@/utils/avatar"

const FIELD_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

export function ContextPanelHeader({ persona }: { persona: PersonaAgent }) {
  const edit = useAgentBuilderStore((s) => s.personaEdited)
  const [name, setName] = useState(persona.name)

  useEffect(() => {
    setName(persona.name)
  }, [persona.cluster_id, persona.name])

  const commit = () => {
    const trimmed = name.trim()
    if (!trimmed || trimmed === persona.name) {
      setName(persona.name)
      return
    }
    edit(persona.cluster_id, { name: trimmed })
  }

  return (
    <div className="flex items-center gap-3 border-b p-4">
      <Avatar className="size-10">
        <AvatarFallback className="bg-muted text-muted-foreground">
          {initials(persona.name)}
        </AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
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
    </div>
  )
}
