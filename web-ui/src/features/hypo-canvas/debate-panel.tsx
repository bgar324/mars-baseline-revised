"use client"

import { Fragment, useMemo } from "react"
import { Lightbulb, Reply, Sparkles, TriangleAlert } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import {
  CitedText,
  buildCitationNumbering,
} from "@/components/common/cited-text"
import { InlineCitation } from "@/components/common/inline-citation"
import { StreamingMarkdown } from "@/components/common/streaming-markdown"
import type { Mention } from "@/components/common/streaming-markdown"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Checkpoint } from "@/components/ui/checkpoint"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { formatElapsed, useElapsed } from "@/features/hypo-canvas/use-elapsed"
import { useDebate } from "@/hooks/use-debate"
import { useHypotheses } from "@/hooks/use-hypotheses"
import { usePapers } from "@/hooks/use-papers"
import { useAgentBuilderStore } from "@/store/agent-builder"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"
import type {
  AgentPhase,
  AgentTurn,
  EvidenceWeight,
  Synthesis,
  TurnAction,
} from "@/types/debate"
import { agentColorClasses, useAgentColors } from "@/utils/agent-color"
import { humanizeEnum } from "@/utils/format"

const PHASE_ICON: Record<AgentPhase, LucideIcon> = {
  proposal: Lightbulb,
  rebuttal: Reply,
  refinement: Sparkles,
}

const ACTION_BY_WEIGHT: Record<EvidenceWeight, TurnAction> = {
  strengthens: "support",
  refines: "support",
  weakens: "concede",
  disputed: "challenge",
  unrelated: "challenge",
}

const LABEL = "font-mono text-xs uppercase tracking-wide text-muted-foreground"

const TAB_TRIGGER =
  "flex-none px-3 data-active:text-primary data-active:after:bg-primary"

function turnAction(turn: AgentTurn): TurnAction | null {
  if (turn.response.action) return turn.response.action
  if (turn.response.evidence_weight)
    return ACTION_BY_WEIGHT[turn.response.evidence_weight]
  return null
}

function usePapersByCorpusId(): Map<string, Paper> {
  const { data: papers } = usePapers()
  return useMemo(() => {
    const map = new Map<string, Paper>()
    if (papers)
      for (const p of papers) {
        if (p.corpus_id != null) map.set(String(p.corpus_id), p)
      }
    return map
  }, [papers])
}

export function DebatePanel() {
  const { data: debate } = useDebate()
  const debateStage = useAgentBuilderStore((s) => s.pipelineStages.debate)
  const debateError = useAgentBuilderStore((s) => s.stageErrors.debate)
  const elapsed = useElapsed("debate")
  const turns = debate?.cycle?.turns ?? []
  const agents = debate?.agents ?? []
  const failed = debateStage === "failed"
  const isRunning =
    !failed && (debateStage === "running" || !debate?.cycle?.synthesis)
  const elapsedText = elapsed != null ? ` · ${formatElapsed(elapsed)}` : ""
  const status = failed
    ? "failed"
    : isRunning
      ? `running${elapsedText}`
      : `${turns.length} turn${turns.length === 1 ? "" : "s"}${elapsedText}`

  return (
    <div className="flex h-full min-w-0 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b px-4 py-3">
        <span className={LABEL}>DEBATE</span>
        <span className={LABEL}>{status}</span>
      </div>
      {failed && (
        <div className="mx-4 mt-3 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
          <span className="text-s text-destructive">
            {debateError ?? "The debate failed to run."}
          </span>
        </div>
      )}
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
          <Conversation turns={turns} isRunning={isRunning} agents={agents} />
        </TabsContent>
        <TabsContent
          value="synthesis"
          className="min-h-0 flex-1 overflow-y-auto px-4 pt-4 pb-4"
        >
          <SynthesisTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Conversation({
  turns,
  isRunning,
  agents,
}: {
  turns: AgentTurn[]
  isRunning: boolean
  agents: PersonaAgent[]
}) {
  const personasById = useMemo(
    () => new Map(agents.map((p) => [String(p.cluster_id), p])),
    [agents],
  )
  const papersByCorpusId = usePapersByCorpusId()
  const agentColors = useAgentColors()
  const mentions = useMemo<Mention[]>(
    () =>
      agents.map((p) => ({
        name: p.name,
        className: agentColorClasses(agentColors[p.cluster_id] ?? p.cluster_id)
          .tint,
      })),
    [agents, agentColors],
  )

  if (turns.length === 0 && !isRunning) {
    return <p className="text-s italic text-muted-foreground">No turns yet.</p>
  }

  const lastIdx = turns.length - 1
  const synthesizing =
    turns.length > 0 && turns[lastIdx].phase === "refinement"

  return (
    <div className="flex flex-col">
      {turns.map((turn, idx) => {
        const prev = idx > 0 ? turns[idx - 1] : null
        const showCheckpoint = !prev || prev.phase !== turn.phase
        return (
          <Fragment key={turn.turn_id}>
            {showCheckpoint && (
              <Checkpoint
                icon={PHASE_ICON[turn.phase]}
                label={turn.phase}
                className={idx === 0 ? "pb-5" : "py-5"}
              />
            )}
            <TurnRow
              turn={turn}
              isStreaming={isRunning && idx === lastIdx}
              persona={personasById.get(turn.agent_id)}
              papersByCorpusId={papersByCorpusId}
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
  papersByCorpusId,
  mentions,
}: {
  turn: AgentTurn
  isStreaming: boolean
  persona: PersonaAgent | undefined
  papersByCorpusId: Map<string, Paper>
  mentions: Mention[]
}) {
  const action = turnAction(turn)
  const evidence = turn.response.evidence
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
          {action && (
            <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {humanizeEnum(action)}
            </span>
          )}
        </div>
        <StreamingMarkdown
          text={turn.response.message}
          isStreaming={isStreaming}
          mentions={mentions}
          className="text-s leading-relaxed text-muted-foreground [&_p]:my-1 [&_p]:text-s [&_p:first-child]:mt-0 [&_p:last-child]:mb-0"
        />
        {evidence.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              sources
            </span>
            {evidence.map((corpusId, i) => {
              const paper = papersByCorpusId.get(corpusId)
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

type CiteProps = {
  papersByCorpusId: Map<string, Paper>
  numberOf: (corpusId: string) => number
}

function SynthesisTab() {
  const { data: synthesis } = useHypotheses()
  const papersByCorpusId = usePapersByCorpusId()
  const numbering = useMemo(() => {
    if (!synthesis) return new Map<string, number>()
    const meta = synthesis.meta_review
    const texts = meta
      ? [meta.problem, meta.previous_work, meta.reasoning, meta.hypothesis]
      : []
    for (const h of synthesis.hypotheses) texts.push(h.grounding.join(" "))
    return buildCitationNumbering(texts)
  }, [synthesis])

  if (!synthesis) {
    return (
      <p className="text-s italic text-muted-foreground">
        Synthesis appears once the debate completes.
      </p>
    )
  }

  const numberOf = (id: string) => numbering.get(id) ?? 0
  return (
    <div className="flex flex-col gap-4 text-s">
      <MetaReview
        synthesis={synthesis}
        papersByCorpusId={papersByCorpusId}
        numberOf={numberOf}
      />
      <HypothesisList
        synthesis={synthesis}
        papersByCorpusId={papersByCorpusId}
        numberOf={numberOf}
      />
    </div>
  )
}

function MetaReview({
  synthesis,
  papersByCorpusId,
  numberOf,
}: { synthesis: Synthesis } & CiteProps) {
  const meta = synthesis.meta_review
  if (!meta) return null
  return (
    <div className="flex flex-col gap-3">
      <Field title="Problem" body={meta.problem} cite={{ papersByCorpusId, numberOf }} />
      <Field
        title="Previous work"
        body={meta.previous_work}
        cite={{ papersByCorpusId, numberOf }}
      />
      <Field title="Reasoning" body={meta.reasoning} cite={{ papersByCorpusId, numberOf }} />
      <Field title="Hypothesis" body={meta.hypothesis} cite={{ papersByCorpusId, numberOf }} />
    </div>
  )
}

function HypothesisList({
  synthesis,
  papersByCorpusId,
  numberOf,
}: { synthesis: Synthesis } & CiteProps) {
  if (synthesis.hypotheses.length === 0) return null
  const bestId = synthesis.best?.candidate_id
  return (
    <div className="flex flex-col gap-2">
      <span className={LABEL}>Candidate hypotheses</span>
      {synthesis.hypotheses.map((h) => {
        const isBest = h.id === bestId
        const grounded = h.grounding
          .map((id) => ({ id, paper: papersByCorpusId.get(id) }))
          .filter((g) => g.paper)
        return (
          <div
            key={h.id}
            className="flex flex-col gap-1.5 rounded-md border px-3 py-2.5"
          >
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] uppercase text-muted-foreground">
                {h.id} · {humanizeEnum(h.claim_type)}
              </span>
              {isBest && (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-primary">
                  best
                </span>
              )}
            </div>
            <p className="text-s leading-snug">{h.proposition}</p>
            {h.warrant && (
              <p className="text-s leading-snug text-muted-foreground">
                {h.warrant}
              </p>
            )}
            {grounded.length > 0 && (
              <div className="mt-0.5 flex flex-wrap items-center gap-1">
                <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  grounding
                </span>
                {grounded.map((g) => (
                  <InlineCitation
                    key={g.id}
                    paper={g.paper!}
                    index={numberOf(g.id)}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function Field({
  title,
  body,
  cite,
}: {
  title: string
  body: string
  cite: CiteProps
}) {
  if (!body) return null
  return (
    <div className="flex flex-col gap-1">
      <span className={LABEL}>{title}</span>
      <p className="text-s leading-relaxed text-muted-foreground">
        <CitedText
          text={body}
          papersByCorpusId={cite.papersByCorpusId}
          numberOf={cite.numberOf}
        />
      </p>
    </div>
  )
}
