"use client"

import { useMutation } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { z } from "zod"

const ExportPayloadSchema = z.record(z.string(), z.unknown())

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function useExportSession() {
  return useMutation({
    mutationFn: async () => {
      const state = useAgentBuilderStore.getState()
      if (!state.queryId) throw new Error("no active query")
      const frontend_snapshot = {
        draft: state.draft,
        committed: state.committed,
        mode: state.mode,
        focalClaim: state.focalClaim,
        pipelineStages: state.pipelineStages,
        pipelineSteps: state.pipelineSteps,
        stageErrors: state.stageErrors,
        personas: state.personas,
        selectedClusterId: state.selectedClusterId,
        personaEdits: state.personaEdits,
        agentColors: state.agentColors,
        stageTimings: state.stageTimings,
      }
      const payload = await fetcher(
        `/api/query/${state.queryId}/export`,
        ExportPayloadSchema,
        {
          method: "POST",
          body: JSON.stringify({ frontend_snapshot }),
        },
      )
      downloadJson(`mars-session-${state.queryId}.json`, payload)
      return payload
    },
  })
}
