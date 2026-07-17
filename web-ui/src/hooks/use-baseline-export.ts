"use client"

import { useMutation } from "@tanstack/react-query"
import { z } from "zod"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"

const ExportPayloadSchema = z.record(z.string(), z.unknown())

function download(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function useBaselineExport() {
  return useMutation({
    mutationFn: async () => {
      const builder = useAgentBuilderStore.getState()
      const baseline = useBaselineStore.getState()
      if (!builder.queryId) throw new Error("no active query")

      const payload = await fetcher(
        `/api/query/${builder.queryId}/export`,
        ExportPayloadSchema,
        {
          method: "POST",
          body: JSON.stringify({
            frontend_snapshot: {
              condition: "baseline",
              route: "/",
              startedAt: baseline.startedAt,
              testMode: baseline.testMode,
              exportedAt: new Date().toISOString(),
              activeAgentIds: baseline.activeAgentIds,
              target: baseline.target,
              personaEdits: builder.personaEdits,
              manualPersonas: baseline.manualPersonas,
              manualPapers: baseline.manualPapers,
              pipelineStages: builder.pipelineStages,
              pipelineSteps: builder.pipelineSteps,
              stageErrors: builder.stageErrors,
              stageTimings: builder.stageTimings,
            },
          }),
        },
      )
      download(`baseline-session-${builder.queryId}.json`, payload)
      return payload
    },
  })
}
