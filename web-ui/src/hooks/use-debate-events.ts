"use client"

import { useEffect } from "react"

import { useDebateStore } from "@/features/hypo-canvas/debate-store"
import { DebateEventSchema } from "@/types/debate"

export function useDebateEvents(debateId: string | null): void {
  const eventReceived = useDebateStore((s) => s.eventReceived)

  useEffect(() => {
    if (!debateId) return
    const source = new EventSource(`/api/debate/${debateId}/events`)
    source.onmessage = (msg) => {
      try {
        const event = DebateEventSchema.parse(JSON.parse(msg.data))
        eventReceived(event)
      } catch (err) {
        console.error("[debate-events] parse failed", err, msg.data)
      }
    }
    source.onerror = (err) => {
      console.warn("[debate-events] stream error", err)
    }
    return () => source.close()
  }, [debateId, eventReceived])
}
