"use client"

import { useMemo } from "react"
import { LoaderCircle } from "lucide-react"

import { InlineCitation } from "@/components/common/inline-citation"
import { StreamingMarkdown } from "@/components/common/streaming-markdown"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { usePapers } from "@/hooks/use-papers"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"
import type { AgentTurn, DebateEvent } from "@/types/debate"
import { initials } from "@/utils/avatar"
import { humanizeEnum } from "@/utils/format"

import { useCycleTurns, useDebateStore } from "./debate-store"

const LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

const TAB_TRIGGER =
  "flex-none px-3 data-active:text-primary data-active:after:bg-primary"

export function DebatePanel({ canvasCycleId }: { canvasCycleId: string }) {
  const cycle = useCycleTurns(canvasCycleId)
  const team = useAgentBuilderStore((s) => s.team)
  const eventLog = useDebateStore((s) => s.eventLog)
  const n = Number(canvasCycleId.slice(1))
  const turns = cycle?.turns ?? []
  const isRunning = !cycle || cycle.status === "running"

  return (
    <div className="flex h-full min-w-0 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b px-4 py-3">
        <span className={LABEL}>DEBATE · cycle {n}</span>
        <span className={LABEL}>
          {isRunning
            ? "running"
            : `${turns.length} turn${turns.length === 1 ? "" : "s"}`}
        </span>
      </div>
      <Tabs
        defaultValue="conversation"
        className="flex min-h-0 flex-1 flex-col gap-0"
      >
        <TabsList variant="line" className="mx-4 mt-2 w-auto justify-start">
          <TabsTrigger value="conversation" className={TAB_TRIGGER}>
            Conversation
          </TabsTrigger>
          <TabsTrigger value="synthesis" className={TAB_TRIGGER}>
            Synthesis
          </TabsTrigger>
        </TabsList>
        <TabsContent
          value="conversation"
          className="min-h-0 flex-1 overflow-y-auto px-4 pt-4 pb-4"
        >
          <Conversation
            turns={turns}
            isRunning={isRunning}
            team={team}
            eventLog={eventLog}
          />
        </TabsContent>
        <TabsContent
          value="synthesis"
          className="min-h-0 flex-1 overflow-y-auto px-4 pt-4 pb-4"
        >
          <SynthesisTab synthesis={cycle?.synthesis ?? null} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Conversation({
  turns,
  isRunning,
  team,
  eventLog,
}: {
  turns: AgentTurn[]
  isRunning: boolean
  team: PersonaAgent[]
  eventLog: DebateEvent[]
}) {
  const personasById = useMemo(
    () => new Map(team.map((p) => [String(p.cluster_id), p])),
    [team],
  )

  if (turns.length === 0 && !isRunning) {
    return (
      <p className="text-s italic text-muted-foreground">No turns yet.</p>
    )
  }

  const lastIdx = turns.length - 1

  return (
    <div className="flex flex-col">
      {isRunning && eventLog.length > 0 && (
        <div className="mb-3 rounded-md border bg-muted/40 px-3 py-2">
          <EventLog events={eventLog} team={team} />
        </div>
      )}
      <div className="flex flex-col divide-y">
        {turns.map((turn, idx) => (
          <TurnRow
            key={turn.turn_id}
            turn={turn}
            index={idx + 1}
            isStreaming={isRunning && idx === lastIdx}
            persona={personasById.get(turn.agent_id)}
          />
        ))}
        {isRunning && (
          <div className="flex items-center gap-2 py-3">
            <LoaderCircle className="size-4 animate-spin text-foreground" />
            <TextShimmer className="text-s">
              Running debate cycle…
            </TextShimmer>
          </div>
        )}
      </div>
    </div>
  )
}

function TurnRow({
  turn,
  index,
  isStreaming,
  persona,
}: {
  turn: AgentTurn
  index: number
  isStreaming: boolean
  persona: PersonaAgent | undefined
}) {
  const { data: papers } = usePapers()
  const papersById = useMemo(() => {
    const map = new Map<string, Paper>()
    if (papers) for (const p of papers) map.set(p.id, p)
    return map
  }, [papers])
  return (
    <div className="flex gap-3 py-3 animate-in fade-in-0 duration-300">
      <Avatar className="mt-0.5 size-8 shrink-0">
        <AvatarFallback className="bg-muted text-[11px] text-muted-foreground">
          {initials(persona?.name ?? "??")}
        </AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-baseline gap-2">
          <span className="text-s font-medium">
            {persona?.name ?? "Unknown agent"}
          </span>
          <span className="font-mono text-[10px] uppercase text-muted-foreground">
            turn {index} · {humanizeEnum(turn.turn_type)}
          </span>
        </div>
        <StreamingMarkdown
          text={turn.message}
          isStreaming={isStreaming}
          className="text-s leading-relaxed text-muted-foreground [&_p]:my-1 [&_p]:text-s [&_p:first-child]:mt-0 [&_p:last-child]:mb-0"
        />
        {turn.evidence && turn.evidence.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              sources
            </span>
            {turn.evidence.map((c, i) => {
              const paper = papersById.get(c.paper_id)
              if (!paper) return null
              return (
                <InlineCitation
                  key={`${paper.id}-${i}`}
                  paper={paper}
                  index={i + 1}
                />
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function SynthesisTab({
  synthesis,
}: {
  synthesis: NonNullable<ReturnType<typeof useCycleTurns>>["synthesis"]
}) {
  if (!synthesis) {
    return (
      <p className="text-s italic text-muted-foreground">
        Synthesis appears once the cycle completes.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-3 text-s">
      {synthesis.points_of_agreement.length > 0 && (
        <Group title="Agreement" items={synthesis.points_of_agreement} />
      )}
      {synthesis.points_of_disagreement.length > 0 && (
        <Group title="Disagreement" items={synthesis.points_of_disagreement} />
      )}
      {synthesis.questions.length > 0 && (
        <Group title="Open questions" items={synthesis.questions} />
      )}
      {synthesis.candidate_hypotheses.length > 0 && (
        <Group
          title="Candidate hypotheses"
          items={synthesis.candidate_hypotheses}
        />
      )}
    </div>
  )
}

function Group({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={LABEL}>{title}</span>
      <ul className="flex flex-col gap-1 pl-4">
        {items.map((item, i) => (
          <li key={i} className="list-disc text-s">
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

function EventLog({
  events,
  team,
}: {
  events: DebateEvent[]
  team: PersonaAgent[]
}) {
  return (
    <ul className="flex flex-col gap-1 font-mono text-xs text-muted-foreground">
      {events.slice(-6).map((event, i) => (
        <li key={i} className="flex items-center gap-2">
          <span className="inline-block size-1.5 rounded-full bg-foreground/60" />
          <span>{event.event}</span>
          <EventDetail event={event} team={team} />
        </li>
      ))}
    </ul>
  )
}

function EventDetail({
  event,
  team,
}: {
  event: DebateEvent
  team: PersonaAgent[]
}) {
  const agentId = (event.payload?.agent_id ?? null) as string | null
  const turnType = (event.payload?.turn_type ?? null) as string | null
  const persona =
    agentId != null
      ? team.find((p) => String(p.cluster_id) === agentId)
      : undefined
  if (event.event === "turn.produced" && persona && turnType) {
    return (
      <span>
        · {persona.name} · {turnType}
      </span>
    )
  }
  if (event.event === "stance.updated" && persona) {
    return <span>· {persona.name}</span>
  }
  return null
}

