"use client"

import { useMemo, useState } from "react"
import { Check } from "lucide-react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { Button } from "@/components/ui/button"
import { rightPanelRef } from "@/features/hypo-canvas/panel-refs"
import { usePersonas } from "@/hooks/use-personas"
import { usePerspectives } from "@/hooks/use-perspectives"
import { useRunDebate } from "@/hooks/use-run-debate"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"
import { humanizeEnum } from "@/utils/format"

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"
const FIELD_LABEL =
  "font-mono text-[10px] uppercase tracking-wide text-muted-foreground"
const MAX_DEBATERS = 4

function AgentCard({
  persona,
  selectable,
  checked,
  onToggle,
}: {
  persona: PersonaAgent
  selectable: boolean
  checked: boolean
  onToggle: (clusterId: number) => void
}) {
  const selected = useAgentBuilderStore((s) => s.selectedClusterId)
  const select = useAgentBuilderStore((s) => s.agentSelected)

  const isSelected = selected === persona.cluster_id

  const onActivate = () => {
    select(persona.cluster_id)
    rightPanelRef.current?.expand()
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onActivate}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          onActivate()
        }
      }}
      className={cn(
        "cursor-pointer rounded-md border bg-background p-3",
        "transition-colors hover:border-ring",
        isSelected && "border-ring",
      )}
    >
      <div className="flex min-w-0 items-center gap-2">
        {selectable && (
          <button
            type="button"
            aria-pressed={checked}
            onClick={(e) => {
              e.stopPropagation()
              onToggle(persona.cluster_id)
            }}
            className={cn(
              "flex size-4 shrink-0 items-center justify-center rounded border transition-colors",
              checked
                ? "border-foreground bg-foreground text-background"
                : "border-muted-foreground/40 text-transparent hover:border-foreground",
            )}
          >
            <Check className="size-3" />
          </button>
        )}
        <AgentAvatar
          clusterId={persona.cluster_id}
          name={persona.name}
          className="size-6"
          fallbackClassName="text-[10px]"
        />
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-xs font-medium">{persona.name}</span>
          <span className="truncate font-mono text-[10px] uppercase text-muted-foreground">
            {humanizeEnum(persona.reasoning_style)}
          </span>
        </div>
      </div>

      <div className="mt-3">
        <div className={cn(FIELD_LABEL, "mb-1.5")}>Framing</div>
        <div className="rounded-md border px-2.5 py-2">
          <p className="line-clamp-2 text-xs leading-snug">
            &ldquo;{persona.framing}&rdquo;
          </p>
        </div>
      </div>
    </div>
  )
}

export function ResearcherPool() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  return <ResearcherPoolInner key={queryId ?? "none"} />
}

function ResearcherPoolInner() {
  const committed = useAgentBuilderStore((s) => s.committed)
  const mode = useAgentBuilderStore((s) => s.mode)
  const debateStage = useAgentBuilderStore((s) => s.pipelineStages.debate)
  const personaEdits = useAgentBuilderStore((s) => s.personaEdits)
  const { data, isFetching, isError } = usePersonas()
  const { data: perspectives } = usePerspectives()
  const runDebate = useRunDebate()

  const debateStarted = debateStage != null && debateStage !== "pending"
  const selectable =
    mode === "manual" && !!data && data.length > 0 && !debateStarted

  const [userChecked, setUserChecked] = useState<Set<number> | null>(null)

  const defaultChecked = useMemo(() => {
    if (perspectives && perspectives.length > 0) return new Set(perspectives)
    if (data) return new Set(data.map((p) => p.cluster_id))
    return new Set<number>()
  }, [perspectives, data])

  const effective = userChecked ?? defaultChecked

  const toggle = (clusterId: number) =>
    setUserChecked((prev) => {
      const next = new Set(prev ?? defaultChecked)
      if (next.has(clusterId)) next.delete(clusterId)
      else next.add(clusterId)
      return next
    })

  const checkedIds = [...effective]
  const selectedPersonas = (data ?? [])
    .filter((persona) => effective.has(persona.cluster_id))
    .map((persona) => ({
      ...persona,
      ...(personaEdits[persona.cluster_id] ?? {}),
    }))
  const invalidSelection =
    checkedIds.length < 2 || checkedIds.length > MAX_DEBATERS

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <span className={SECTION_LABEL}>
        Researchers{data ? ` (${data.length})` : ""}
      </span>

      {selectable && (
        <div className="flex flex-col gap-1.5">
          <Button
            size="sm"
            onClick={() => runDebate.mutate(selectedPersonas)}
            disabled={invalidSelection || runDebate.isPending}
          >
            Run debate ({checkedIds.length})
          </Button>
          {checkedIds.length < 2 && (
            <p className="text-xs text-muted-foreground">
              Select at least 2 researchers to debate.
            </p>
          )}
          {checkedIds.length > MAX_DEBATERS && (
            <p className="text-xs text-muted-foreground">
              Select no more than {MAX_DEBATERS} researchers to control study
              latency.
            </p>
          )}
          {runDebate.isError && (
            <p className="text-xs text-destructive">
              Couldn&rsquo;t start the debate. Please try again.
            </p>
          )}
        </div>
      )}

      {!committed ? (
        <p className="text-s text-muted-foreground">No researchers yet.</p>
      ) : isError ? (
        <p className="text-s text-muted-foreground">
          This session is no longer available. Use{" "}
          <span className="font-medium">Revise</span> to start a new one.
        </p>
      ) : isFetching && !data ? (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-14 w-full animate-pulse rounded-md bg-muted"
            />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <p className="text-s text-muted-foreground">No researchers yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {data.map((persona) => (
            <AgentCard
              key={persona.cluster_id}
              persona={persona}
              selectable={selectable}
              checked={effective.has(persona.cluster_id)}
              onToggle={toggle}
            />
          ))}
        </div>
      )}
    </div>
  )
}
