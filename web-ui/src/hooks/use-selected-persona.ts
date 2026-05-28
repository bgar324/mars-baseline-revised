"use client"

import { usePersonas } from "@/hooks/use-personas"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"

export function useSelectedPersona(): PersonaAgent | null {
  const selected = useAgentBuilderStore((s) => s.selectedClusterId)
  const edits = useAgentBuilderStore((s) => s.personaEdits)
  const { data } = usePersonas()

  if (selected == null || !data) return null
  const base = data.find((p) => p.cluster_id === selected)
  if (!base) return null
  return { ...base, ...edits[selected] }
}
