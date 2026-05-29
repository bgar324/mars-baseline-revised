"use client"

import { Fragment, useMemo } from "react"
import { Lightbulb, Reply, Sparkles } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { InlineCitation } from "@/components/common/inline-citation"
import { StreamingMarkdown } from "@/components/common/streaming-markdown"
import type { Mention } from "@/components/common/streaming-markdown"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Checkpoint } from "@/components/ui/checkpoint"
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
import type { AgentTurn, TurnType } from "@/types/debate"
import { agentColorClasses, useAgentColors } from "@/utils/agent-color"
import { humanizeEnum } from "@/utils/format"

import { useCycleTurns } from "./debate-store"

const PHASE_ICON: Record<TurnType, LucideIcon> = {
  propose: Lightbulb,
  respond: Reply,
  refine: Sparkles,
}

const LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

const TAB_TRIGGER =
  "flex-none px-3 data-active:text-primary data-active:after:bg-primary"

export function DebatePanel({ canvasCycleId }: { canvasCycleId: string }) {
  const cycle = useCycleTurns(canvasCycleId)
  const team = useAgentBuilderStore((s) => s.team)
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
          <Conversation turns={turns} isRunning={isRunning} team={team} />
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
}: {
  turns: AgentTurn[]
  isRunning: boolean
  team: PersonaAgent[]
}) {
  const personasById = useMemo(
    () => new Map(team.map((p) => [String(p.cluster_id), p])),
    [team],
  )
  const agentColors = useAgentColors()
  const mentions = useMemo<Mention[]>(
    () =>
      team.map((p) => ({
        name: p.name,
        className: agentColorClasses(agentColors[p.cluster_id] ?? p.cluster_id)
          .tint,
      })),
    [team, agentColors],
  )

  if (turns.length === 0 && !isRunning) {
    return (
      <p className="text-s italic text-muted-foreground">No turns yet.</p>
    )
  }

  const lastIdx = turns.length - 1
  const synthesizing =
    turns.length > 0 && turns[lastIdx].turn_type === "refine"

  return (
    <div className="flex flex-col">
      {turns.map((turn, idx) => {
        const prev = idx > 0 ? turns[idx - 1] : null
        const showCheckpoint = !prev || prev.turn_type !== turn.turn_type
        return (
          <Fragment key={turn.turn_id}>
            {showCheckpoint && (
              <Checkpoint
                icon={PHASE_ICON[turn.turn_type]}
                label={turn.turn_type}
                className={idx === 0 ? "pb-5" : "py-5"}
              />
            )}
            <TurnRow
              turn={turn}
              isStreaming={isRunning && idx === lastIdx}
              persona={personasById.get(turn.agent_id)}
              mentions={mentions}
            />
          </Fragment>
        )
      })}
      {isRunning && (
        <div className="py-3">
          <TextShimmer className="text-s">
            {synthesizing ? "Synthesizing…" : "Thinking…"}
          </TextShimmer>
        </div>
      )}
    </div>
  )
}

function TurnRow({
  turn,
  isStreaming,
  persona,
  mentions,
}: {
  turn: AgentTurn
  isStreaming: boolean
  persona: PersonaAgent | undefined
  mentions: Mention[]
}) {
  const { data: papers } = usePapers()
  const papersById = useMemo(() => {
    const map = new Map<string, Paper>()
    if (papers) for (const p of papers) map.set(p.id, p)
    return map
  }, [papers])
  return (
    <div className="flex gap-2.5 py-3 animate-in fade-in-0 duration-300">
      {persona ? (
        <AgentAvatar
          clusterId={persona.cluster_id}
          name={persona.name}
          className="mt-0.5 size-5 shrink-0"
          fallbackClassName="pt-px text-[9px] leading-none"
        />
      ) : (
        <Avatar className="mt-0.5 size-5 shrink-0">
          <AvatarFallback className="bg-muted pt-px text-[9px] leading-none text-muted-foreground">
            ??
          </AvatarFallback>
        </Avatar>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <span className="text-s font-medium">
            {persona?.name ?? "Unknown agent"}
          </span>
          {turn.response_action && (
            <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {humanizeEnum(turn.response_action)}
            </span>
          )}
        </div>
        <StreamingMarkdown
          text={turn.message}
          isStreaming={isStreaming}
          mentions={mentions}
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


