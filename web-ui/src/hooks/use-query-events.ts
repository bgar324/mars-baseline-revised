"use client"

import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"

import { clearStaleQuery } from "@/hooks/use-stale-query"
import { useAgentBuilderStore } from "@/store/agent-builder"
import {
  PipelineEventSchema,
  PipelineStateSchema,
  type StageName,
} from "@/types/query"

const ARTIFACT_KEY: Partial<Record<StageName, string>> = {
  extract: "extraction",
  retrieve: "papers",
  cluster: "clusters",
  persona: "personas",
  debate: "debate",
}

function payloadError(payload: unknown): string | undefined {
  if (payload && typeof payload === "object" && "error" in payload) {
    const e = (payload as { error?: unknown }).error
    return typeof e === "string" ? e : undefined
  }
  return undefined
}

export function useQueryEvents(queryId: string | null): void {
  const qc = useQueryClient()

  useEffect(() => {
    if (!queryId) return
    let closed = false
    const set = useAgentBuilderStore.getState().pipelineStageSet

    const invalidate = (stage: StageName) => {
      const key = ARTIFACT_KEY[stage]
      if (key) qc.invalidateQueries({ queryKey: [key, queryId] })
      if (stage === "debate")
        qc.invalidateQueries({ queryKey: ["hypotheses", queryId] })
    }

    fetch(`/api/query/${queryId}`)
      .then(async (r) => {
        if (r.ok) return r.json()
        if (r.status === 404) clearStaleQuery({ status: 404 })
        return null
      })
      .then((json) => {
        if (closed || !json) return
        const parsed = PipelineStateSchema.safeParse(json)
        if (!parsed.success) return
        for (const [stage, node] of Object.entries(parsed.data.stages)) {
          set(stage as StageName, node.status, node.error ?? undefined)
          if (node.status === "complete") invalidate(stage as StageName)
        }
      })
      .catch(() => {})

    const source = new EventSource(`/api/query/${queryId}/events`)
    source.onmessage = (msg) => {
      let event
      try {
        event = PipelineEventSchema.parse(JSON.parse(msg.data))
      } catch (err) {
        console.error("[query-events] parse failed", err, msg.data)
        return
      }
      const stage = event.stage ?? undefined
      switch (event.event) {
        case "stage.started":
          if (stage) set(stage, "running")
          break
        case "query.decomposed":
          set("extract", "complete")
          invalidate("extract")
          break
        case "papers.retrieved":
          set("retrieve", "complete")
          invalidate("retrieve")
          break
        case "clusters.generated":
          set("cluster", "complete")
          invalidate("cluster")
          break
        case "personas.created":
          set("persona", "complete")
          invalidate("persona")
          break
        case "stage.completed":
          if (stage) {
            set(stage, "complete")
            invalidate(stage)
          }
          if (stage === "debate") source.close()
          break
        case "stage.skipped":
          if (stage) set(stage, "skipped")
          if (stage === "debate") source.close()
          break
        case "stage.failed":
          if (stage) set(stage, "failed", payloadError(event.payload))
          if (stage === "debate") source.close()
          break
        default:
          break
      }
    }
    source.onerror = (err) => {
      console.warn("[query-events] stream error", err)
    }

    return () => {
      closed = true
      source.close()
    }
  }, [queryId, qc])
}
