"use client"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { rightPanelRef } from "@/features/hypo-canvas/panel-refs"
import { usePersonas } from "@/hooks/use-personas"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"
import { humanizeEnum } from "@/utils/format"

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"
const FIELD_LABEL =
  "font-mono text-[10px] uppercase tracking-wide text-muted-foreground"

function AgentCard({ persona }: { persona: PersonaAgent }) {
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
  const committed = useAgentBuilderStore((s) => s.committed)
  const { data, isFetching, isError } = usePersonas()

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <span className={SECTION_LABEL}>
        Researchers{data ? ` (${data.length})` : ""}
      </span>

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
            <AgentCard key={persona.cluster_id} persona={persona} />
          ))}
        </div>
      )}
    </div>
  )
}
