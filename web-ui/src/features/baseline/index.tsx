"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import {
  ArrowRight,
  Check,
  ChevronDown,
  Download,
  FlaskConical,
  Menu,
  MessageSquareText,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from "lucide-react"

import { AgentAvatar } from "@/components/common/agent-avatar"
import { InlineCitation } from "@/components/common/inline-citation"
import { StreamingMarkdown } from "@/components/common/streaming-markdown"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { InstructionsEditor } from "@/features/agent-builder/context-panel/instructions-editor"
import { useBaselineChat, useSendBaselineMessage } from "@/hooks/use-baseline-chat"
import { useBaselineExport } from "@/hooks/use-baseline-export"
import { useCreateBaseline } from "@/hooks/use-create-baseline"
import { useDebate } from "@/hooks/use-debate"
import { useHypotheses } from "@/hooks/use-hypotheses"
import { usePapers } from "@/hooks/use-papers"
import { usePersonas } from "@/hooks/use-personas"
import { useQueryEvents } from "@/hooks/use-query-events"
import { useRunDebate } from "@/hooks/use-run-debate"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"
import type { BaselineMessage } from "@/types/baseline"
import type { AgentTurn, EvidenceSet, Synthesis } from "@/types/debate"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"
import { humanizeEnum } from "@/utils/format"

const LABEL = "font-mono text-xs uppercase tracking-wide text-muted-foreground"
const STAGES = ["extract", "retrieve", "cluster", "persona"] as const

const SETUP_ACTIVITIES: Record<
  string,
  { label: string; detail: string }
> = {
  "query.extract_spans": {
    label: "Identifying the research constructs",
    detail: "Separating the domain, intended outcome, key concepts, and proposed relationship.",
  },
  "query.synthesize_claim": {
    label: "Forming a testable focal claim",
    detail: "Restating the research question as one relationship the team can examine and challenge.",
  },
  "query.expand_query": {
    label: "Expanding the research terminology",
    detail: "Finding related terms and measures that may appear in adjacent literature.",
  },
  "query.generate_questions": {
    label: "Drafting literature-search questions",
    detail: "Creating evidence-oriented queries that resemble relevant paper titles and abstracts.",
  },
  "retrieval.build_anchors": {
    label: "Building semantic search anchors",
    detail: "Combining the focal claim and expanded concepts into literature-search targets.",
  },
  "retrieval.generate_search_variants": {
    label: "Generating search variants",
    detail: "Rephrasing the research problem to cover different terminology used across fields.",
  },
  "retrieval.retrieve_candidates": {
    label: "Searching for relevant research",
    detail: "Running semantic snippet searches, hydrating paper records, and removing duplicates.",
  },
  "retrieval.expand_corpus": {
    label: "Expanding the evidence set",
    detail: "Using highly cited seed papers to retrieve related recommendations beyond the initial results.",
  },
  "cluster.embed_papers": {
    label: "Representing papers by topic",
    detail: "Preparing the retrieved literature for perspective discovery.",
  },
  "cluster.cluster_papers": {
    label: "Mapping research perspectives",
    detail: "Grouping papers by similarity in their scientific embedding representations.",
  },
  "cluster.select_perspectives": {
    label: "Selecting distinct perspectives",
    detail: "Selecting cluster centroids that are separated in embedding space.",
  },
  "persona.synthesize_personas": {
    label: "Drafting researcher profiles",
    detail: "Turning each evidence cluster into a grounded framing, reasoning style, and evaluation lens.",
  },
  "persona.select_panel": {
    label: "Finalizing the research team",
    detail: "Preparing the generated researcher profiles for manual selection.",
  },
}

const SETUP_STEP_ORDER: Record<(typeof STAGES)[number], string[]> = {
  extract: [
    "query.extract_spans",
    "query.synthesize_claim",
    "query.expand_query",
    "query.generate_questions",
  ],
  retrieve: [
    "retrieval.build_anchors",
    "retrieval.generate_search_variants",
    "retrieval.retrieve_candidates",
    "retrieval.expand_corpus",
  ],
  cluster: [
    "cluster.embed_papers",
    "cluster.cluster_papers",
    "cluster.select_perspectives",
  ],
  persona: ["persona.synthesize_personas", "persona.select_panel"],
}

function getSetupActivity(
  stage: (typeof STAGES)[number],
  steps: Record<string, string | undefined>,
) {
  const configured = SETUP_STEP_ORDER[stage]
  const available = configured.filter((step) => steps[step] != null)
  const ordered = available.length > 0 ? available : configured
  let index = ordered.findIndex((step) => steps[step] === "running")
  if (index === -1) {
    index = ordered.findIndex(
      (step) => steps[step] === "pending" || steps[step] == null,
    )
  }
  if (index === -1) index = ordered.length - 1
  const step = ordered[index]
  return {
    ...SETUP_ACTIVITIES[step],
    index: index + 1,
    total: ordered.length,
  }
}

const DEBATE_ACTIVITIES = [
  {
    step: "debate.prepare_evidence",
    label: "Reviewing relevant literature",
    cardLabel: "Searching and reviewing evidence",
    detail: "Each researcher is retrieving evidence relevant to their perspective.",
  },
  {
    step: "debate.proposal",
    label: "Drafting initial positions",
    cardLabel: "Formulating an initial position",
    detail: "Researchers are turning the retrieved findings into evidence-backed positions.",
  },
  {
    step: "debate.assessment",
    label: "Comparing researcher positions",
    cardLabel: "Comparing perspectives",
    detail: "The system is identifying agreements, disagreements, and open questions.",
  },
  {
    step: "debate.rebuttal",
    label: "Stress-testing assumptions",
    cardLabel: "Testing the position against alternatives",
    detail: "Researchers are challenging one another's mechanisms and evidence.",
  },
  {
    step: "debate.refinement",
    label: "Refining testable claims",
    cardLabel: "Refining the hypothesis",
    detail: "Each perspective is narrowing its claim in response to the discussion.",
  },
  {
    step: "debate.adjudication",
    label: "Checking disputed claims",
    cardLabel: "Checking claims against evidence",
    detail: "The strongest points are being checked against the retrieved literature.",
  },
  {
    step: "debate.synthesis",
    label: "Generating candidate hypotheses",
    cardLabel: "Contributing to candidate hypotheses",
    detail: "Distinct, testable hypotheses are being extracted from the discussion.",
  },
  {
    step: "debate.select_best",
    label: "Selecting the strongest hypothesis",
    cardLabel: "Evaluating the candidate hypotheses",
    detail: "Candidates are being compared for relevance, grounding, and testability.",
  },
  {
    step: "debate.compose",
    label: "Composing the research artifact",
    cardLabel: "Finalizing the research artifact",
    detail: "The evidence, reasoning, and selected hypothesis are being assembled.",
  },
] as const

type DebateActivity = (typeof DEBATE_ACTIVITIES)[number] & {
  index: number
  total: number
}

function getDebateActivity(
  steps: Record<string, string | undefined>,
): DebateActivity {
  let index = DEBATE_ACTIVITIES.findIndex(
    (activity) => steps[activity.step] === "running",
  )
  if (index === -1) {
    index = DEBATE_ACTIVITIES.findIndex(
      (activity) =>
        steps[activity.step] === "pending" || steps[activity.step] == null,
    )
  }
  if (index === -1) index = DEBATE_ACTIVITIES.length - 1
  return {
    ...DEBATE_ACTIVITIES[index],
    index: index + 1,
    total: DEBATE_ACTIVITIES.length,
  }
}

export function BaselineWorkspace() {
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const condition = useAgentBuilderStore((state) => state.studyCondition)
  const personaStage = useAgentBuilderStore(
    (state) => state.pipelineStages.persona,
  )
  const isBaseline = condition === "baseline"

  useQueryEvents(isBaseline ? queryId : null)
  usePersonas()
  usePapers()
  useDebate()
  useHypotheses()
  useBaselineChat()

  if (!queryId || !isBaseline) return <StartScreen />
  if (personaStage !== "complete") return <PipelineScreen />
  return <DiscussionWorkspace />
}

function StartScreen() {
  const [problem, setProblem] = useState("")
  const create = useCreateBaseline()
  const canSubmit = problem.trim().length > 0 && !create.isPending

  const submit = (testMode = false) => {
    if (canSubmit) create.mutate({ text: problem.trim(), testMode })
  }

  return (
    <main className="relative flex min-h-dvh overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:44px_44px] opacity-25" />
      <aside className="relative hidden w-56 shrink-0 border-r bg-sidebar/70 px-7 py-8 md:flex md:flex-col">
        <div>
          <div className="font-serif text-xl tracking-tight">MARS</div>
        </div>
      </aside>

      <section className="relative flex flex-1 items-center justify-center px-5 py-16">
        <div className="w-full max-w-2xl animate-in fade-in-0 slide-in-from-bottom-2 duration-500">
          <h1 className="max-w-xl font-serif text-4xl leading-tight tracking-tight sm:text-5xl">
            What question should the research team examine?
          </h1>
          <p className="mt-4 max-w-lg text-s leading-relaxed text-muted-foreground">
            MARS will retrieve relevant literature, assemble researcher
            perspectives, and prepare a working hypothesis for discussion.
          </p>

          <div className="mt-9 rounded-xl border bg-card p-2 shadow-lg">
            <Textarea
              autoFocus
              value={problem}
              onChange={(event) => setProblem(event.target.value)}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                  event.preventDefault()
                  submit(false)
                }
              }}
              placeholder="Describe a research problem, question, or early hypothesis..."
              className="min-h-36 resize-none border-0 bg-transparent px-4 py-3 text-m shadow-none focus-visible:ring-0 md:text-m"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 pt-2">
              <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                ⌘ Enter to begin
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => submit(true)}
                  disabled={!canSubmit}
                >
                  {create.isPending && create.variables?.testMode
                    ? "Starting preview..."
                    : "Test UI · no model spend"}
                </Button>
                <Button onClick={() => submit(false)} disabled={!canSubmit}>
                  {create.isPending && !create.variables?.testMode
                    ? "Starting..."
                    : "Build research team"}
                  <ArrowRight />
                </Button>
              </div>
            </div>
          </div>
          {create.error && (
            <p className="mt-3 text-s text-destructive">
              Could not start the session. Check that the MARS backend is
              running and try again.
            </p>
          )}
        </div>
      </section>
    </main>
  )
}

function PipelineScreen() {
  const committed = useAgentBuilderStore((state) => state.committed)
  const stages = useAgentBuilderStore((state) => state.pipelineStages)
  const pipelineSteps = useAgentBuilderStore((state) => state.pipelineSteps)
  const errors = useAgentBuilderStore((state) => state.stageErrors)
  const failed = STAGES.find((stage) => stages[stage] === "failed")
  const runningStage = STAGES.find((stage) => stages[stage] === "running")
  const activity = runningStage
    ? getSetupActivity(runningStage, pipelineSteps)
    : null

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-5">
      <div className="w-full max-w-xl">
        <h1 className="font-serif text-3xl tracking-tight">
          Building an evidence-grounded research team
        </h1>
        <p className="mt-3 line-clamp-3 text-s leading-relaxed text-muted-foreground">
          {committed}
        </p>

        {activity && runningStage && (
          <div
            className="mt-6 rounded-lg border border-primary/25 bg-primary/4 px-4 py-3.5"
            role="status"
            aria-live="polite"
          >
            <div className="flex items-start gap-3">
              <span className="mt-1.5 size-2 shrink-0 animate-pulse rounded-full bg-primary" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <TextShimmer className="text-s font-medium">
                    {activity.label}
                  </TextShimmer>
                  <span className="font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
                    {activity.index}/{activity.total}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {activity.detail}
                </p>
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                    style={{
                      width: `${(activity.index / activity.total) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 overflow-hidden rounded-lg border bg-card">
          {STAGES.map((stage, index) => {
            const status = stages[stage] ?? "pending"
            return (
              <div
                key={stage}
                className="flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
              >
                <div
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full border font-mono text-[9px]",
                    status === "complete" &&
                      "border-primary bg-primary text-primary-foreground",
                    status === "running" && "border-primary text-primary",
                    status === "failed" &&
                      "border-destructive text-destructive",
                  )}
                >
                  {status === "complete" ? <Check className="size-3" /> : index + 1}
                </div>
                <span className="text-s font-medium">
                  {stage === "extract" && "Analyze research problem"}
                  {stage === "retrieve" && "Retrieve relevant literature"}
                  {stage === "cluster" && "Map research perspectives"}
                  {stage === "persona" && "Generate researcher profiles"}
                </span>
                <span className="ml-auto font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  {status === "running" ? (
                    <TextShimmer>
                      {stage === runningStage && activity
                        ? `${activity.index}/${activity.total}`
                        : "working"}
                    </TextShimmer>
                  ) : (
                    status
                  )}
                </span>
              </div>
            )
          })}
        </div>
        {failed ? (
          <p className="mt-4 text-s text-destructive">
            {errors[failed] ?? `The ${failed} stage failed.`}
          </p>
        ) : null}
      </div>
    </main>
  )
}

function DiscussionWorkspace() {
  const queryClient = useQueryClient()
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const committed = useAgentBuilderStore((state) => state.committed)
  const personas = useAgentBuilderStore((state) => state.personas)
  const edits = useAgentBuilderStore((state) => state.personaEdits)
  const clearBuilder = useAgentBuilderStore(
    (state) => state.researchProblemCleared,
  )
  const { data: debate } = useDebate()
  const { data: synthesis } = useHypotheses()
  const { data: conversation } = useBaselineChat()
  const { data: papers } = usePapers()
  const exportSession = useBaselineExport()
  const resetBaseline = useBaselineStore((state) => state.reset)
  const testMode = useBaselineStore((state) => state.testMode)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  const mergedPersonas = useMemo(
    () => personas.map((persona) => ({ ...persona, ...edits[persona.cluster_id] })),
    [personas, edits],
  )

  const reset = () => {
    resetBaseline()
    clearBuilder()
    queryClient.clear()
  }

  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-background">
      <header className="flex h-12 shrink-0 items-center border-b bg-background px-3 sm:px-4">
        <Button
          size="icon-xs"
          variant="ghost"
          className="mr-2 md:hidden"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open researcher panel"
        >
          <Menu />
        </Button>
        <div className="flex min-w-0 items-baseline gap-3">
          <span className="shrink-0 font-serif text-l">MARS</span>
          {testMode && (
            <span className="rounded-full border border-primary/30 bg-primary/5 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-primary">
              Test mode · no model calls
            </span>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="outline"
            size="xs"
            disabled={!queryId || exportSession.isPending}
            onClick={() => exportSession.mutate()}
          >
            <Download />
            <span className="hidden sm:inline">Export</span>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="xs">
                <RotateCcw />
                <span className="hidden sm:inline">Reset</span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle className="tracking-normal">
                  Discard this discussion?
                </AlertDialogTitle>
                <AlertDialogDescription>
                  The research team, hypotheses, and conversation will be
                  cleared from this browser.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep current</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={reset}>
                  Discard
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div
          className={cn(
            "fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm transition-opacity md:hidden",
            sidebarOpen ? "opacity-100" : "pointer-events-none opacity-0",
          )}
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 flex w-[min(88vw,360px)] min-h-0 flex-col border-r bg-sidebar transition-transform duration-200 md:static md:z-auto md:w-[340px] md:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex h-12 shrink-0 items-center justify-between border-b px-4 md:hidden">
            <span className={LABEL}>Research team</span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close researcher panel"
            >
              <X />
            </Button>
          </div>
          <ResearcherSidebar
            personas={mergedPersonas}
            turns={debate?.cycle?.turns ?? []}
            evidence={debate?.cycle?.evidence ?? {}}
            papers={papers ?? []}
            onEdit={setEditingId}
            onStarted={() => setSidebarOpen(false)}
          />
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="shrink-0 border-b px-4 py-3 sm:px-8">
            <div className="mx-auto max-w-3xl">
              <span className={LABEL}>Research problem</span>
              <p className="mt-1 text-s leading-relaxed font-medium whitespace-normal">
                {committed}
              </p>
            </div>
          </div>
          <ConversationPanel
            personas={mergedPersonas}
            synthesis={synthesis}
            messages={conversation?.messages ?? []}
            papers={papers ?? []}
          />
        </main>
      </div>

      {editingId != null && (
        <PersonaEditor
          persona={mergedPersonas.find((item) => item.cluster_id === editingId)}
          onClose={() => setEditingId(null)}
        />
      )}
    </div>
  )
}

function ResearcherSidebar({
  personas,
  turns,
  evidence,
  papers,
  onEdit,
  onStarted,
}: {
  personas: PersonaAgent[]
  turns: AgentTurn[]
  evidence: Record<string, EvidenceSet>
  papers: Paper[]
  onEdit: (id: number) => void
  onStarted: () => void
}) {
  const activeIds = useBaselineStore((state) => state.activeAgentIds)
  const activeAgentsSet = useBaselineStore((state) => state.activeAgentsSet)
  const target = useBaselineStore((state) => state.target)
  const targetSet = useBaselineStore((state) => state.targetSet)
  const debateStage = useAgentBuilderStore((state) => state.pipelineStages.debate)
  const debateError = useAgentBuilderStore((state) => state.stageErrors.debate)
  const pipelineSteps = useAgentBuilderStore((state) => state.pipelineSteps)
  const runDebate = useRunDebate()
  const locked = debateStage === "running" || debateStage === "complete"
  const activity = getDebateActivity(pipelineSteps)

  useEffect(() => {
    if (personas.length > 0 && activeIds.length === 0 && !locked) {
      activeAgentsSet(personas.slice(0, 4).map((persona) => persona.cluster_id))
    }
  }, [personas, activeIds.length, activeAgentsSet, locked])

  const toggle = (clusterId: number) => {
    if (locked) return
    const active = activeIds.includes(clusterId)
    if (!active && activeIds.length >= 4) return
    const next = active
      ? activeIds.filter((id) => id !== clusterId)
      : [...activeIds, clusterId]
    activeAgentsSet(next)
    if (typeof target === "number" && !next.includes(target)) targetSet("all")
  }

  const selected = personas.filter((persona) =>
    activeIds.includes(persona.cluster_id),
  )
  const canGenerate = selected.length >= 2 && selected.length <= 4 && !locked

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b px-4 py-3">
        <div className="flex items-end justify-between gap-2">
          <div>
            <span className={LABEL}>Researcher perspectives</span>
            <p className="mt-1 text-xs text-muted-foreground">
              Select 2–4 researchers for the discussion.
            </p>
          </div>
          <span className="font-mono text-[10px] text-muted-foreground">
            {activeIds.length}/4
          </span>
        </div>
        <Button
          className="mt-3 w-full"
          variant={locked ? "outline" : "shine"}
          disabled={!canGenerate}
          onClick={() => {
            runDebate.mutate(selected)
            onStarted()
          }}
        >
          <Sparkles />
          {debateStage === "running"
            ? activity.label
            : debateStage === "complete"
              ? "Hypotheses generated"
              : "Generate hypotheses"}
        </Button>
        {debateStage === "running" && (
          <div className="mt-2" role="status" aria-live="polite">
            <div className="mb-1.5 flex items-center justify-between gap-2 font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
              <span className="truncate">Generating hypotheses</span>
              <span>
                Step {activity.index} of {activity.total}
              </span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-500"
                style={{ width: `${(activity.index / activity.total) * 100}%` }}
              />
            </div>
          </div>
        )}
        {(runDebate.error || debateError) && (
          <p className="mt-2 text-xs text-destructive">
            {debateError ?? "Could not generate hypotheses."}
          </p>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="flex flex-col gap-2.5">
          {personas.map((persona) => {
            const active = activeIds.includes(persona.cluster_id)
            const agentEvidence = evidence[String(persona.cluster_id)]
            const proposal = turns.find(
              (turn) =>
                turn.agent_id === String(persona.cluster_id) &&
                turn.phase === "proposal",
            )
            return (
              <ResearcherCard
                key={persona.cluster_id}
                persona={persona}
                active={active}
                locked={locked}
                loading={debateStage === "running" && active}
                proposal={proposal}
                activity={activity}
                evidenceCount={
                  agentEvidence?.snippets.length ?? 0
                }
                previousWork={formatPreviousWork(
                  persona,
                  proposal,
                  papers,
                  agentEvidence,
                )}
                onToggle={() => toggle(persona.cluster_id)}
                onEdit={() => onEdit(persona.cluster_id)}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ResearcherCard({
  persona,
  active,
  locked,
  loading,
  proposal,
  activity,
  evidenceCount,
  previousWork,
  onToggle,
  onEdit,
}: {
  persona: PersonaAgent
  active: boolean
  locked: boolean
  loading: boolean
  proposal: AgentTurn | undefined
  activity: DebateActivity
  evidenceCount: number
  previousWork: string
  onToggle: () => void
  onEdit: () => void
}) {
  return (
    <div
      role={!locked ? "button" : undefined}
      tabIndex={!locked ? 0 : undefined}
      onClick={!locked ? onEdit : undefined}
      onKeyDown={
        !locked
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault()
                onEdit()
              }
            }
          : undefined
      }
      className={cn(
        "overflow-hidden rounded-lg border bg-background transition-colors",
        active && "border-primary/45",
        !active && "opacity-65",
        !locked && "cursor-pointer hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
      )}
    >
      <div className="px-3 py-3">
        <div className="flex items-center gap-2.5">
          <AgentAvatar
            clusterId={persona.cluster_id}
            name={persona.name}
            className="size-8"
            fallbackClassName="text-[10px]"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-s font-medium">{persona.name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {persona.role || "Researcher"}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={active}
            aria-label={`${active ? "Deactivate" : "Activate"} ${persona.name}`}
            disabled={locked}
            onClick={(event) => {
              event.stopPropagation()
              onToggle()
            }}
            onKeyDown={(event) => event.stopPropagation()}
            className={cn(
              "relative h-5 w-9 shrink-0 rounded-full border transition-colors",
              active ? "border-primary bg-primary" : "bg-muted",
              locked && "cursor-not-allowed",
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 left-0.5 size-3.5 rounded-full bg-background shadow-sm transition-transform",
                active && "translate-x-4",
              )}
            />
          </button>
        </div>
        <div className="mt-3">
          <span className="font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
            Perspective
          </span>
          <p className="mt-1 line-clamp-4 text-xs leading-relaxed text-muted-foreground">
            {persona.perspective || persona.framing}
          </p>
        </div>
      </div>

      {active && (loading || proposal) && (
        <div className="border-t bg-muted/20 px-3 py-3">
          {loading && (
            <div className={cn("flex items-start gap-2.5", proposal && "mb-3 border-b pb-3")}>
              <span className="mt-1.5 size-1.5 shrink-0 animate-pulse rounded-full bg-primary" />
              <div className="min-w-0">
                <TextShimmer className="text-xs">
                  {activity.cardLabel}
                </TextShimmer>
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                  {evidenceCount > 0
                    ? `Working from ${evidenceCount} retrieved evidence passage${evidenceCount === 1 ? "" : "s"}.`
                    : "Locating evidence relevant to this perspective."}
                </p>
              </div>
            </div>
          )}
          {proposal && (
            <div className="space-y-2.5">
              <HypothesisField
                kind="previous"
                label="Previous work"
                text={previousWork}
              />
              <HypothesisField
                kind="reasoning"
                label="Reasoning"
                text={proposal.response.rationale}
              />
              <HypothesisField
                kind="hypothesis"
                label="Hypothesis"
                text={proposal.response.claim}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function HypothesisField({
  kind,
  label,
  text,
}: {
  kind: "previous" | "reasoning" | "hypothesis"
  label: string
  text: string
}) {
  return (
    <div
      className={cn(
        "rounded-r-md border-l-2 bg-background/70 px-3 py-2.5",
        kind === "previous" && "border-l-agent-5",
        kind === "reasoning" && "border-l-agent-2",
        kind === "hypothesis" && "border-l-agent-3 bg-agent-3/5",
      )}
    >
      <span
        className={cn(
          "font-mono text-[9px] uppercase tracking-wide",
          kind === "previous" && "text-agent-5",
          kind === "reasoning" && "text-agent-2",
          kind === "hypothesis" && "text-agent-3",
        )}
      >
        {label}
      </span>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        {text}
      </p>
    </div>
  )
}

function formatPreviousWork(
  persona: PersonaAgent,
  proposal: AgentTurn | undefined,
  papers: Paper[],
  evidence: EvidenceSet | undefined,
): string {
  const byCorpusId = new Map(
    papers
      .filter((paper) => paper.corpus_id != null)
      .map((paper) => [String(paper.corpus_id), paper]),
  )
  const byId = new Map(papers.map((paper) => [paper.id, paper]))
  const snippetsByCorpusId = new Map(
    (evidence?.snippets ?? []).map((snippet) => [snippet.corpus_id, snippet]),
  )
  const citedIds = proposal?.response.evidence ?? []
  const cited = citedIds
    .map((id) => byCorpusId.get(id) ?? byId.get(id))
    .filter((paper): paper is Paper => !!paper)
  const referenced = persona.references
    .map((id) => byId.get(id))
    .filter((paper): paper is Paper => !!paper)
  const selected = [...new Map([...cited, ...referenced].map((paper) => [paper.id, paper])).values()].slice(0, 4)
  const paperEntries = selected
    .map((paper) => {
      const author = paper.authors[0]?.name
      const authorText = author
        ? `${author}${paper.authors.length > 1 ? " et al." : ""}`
        : null
      const year = paper.year ? ` (${paper.year})` : ""
      return authorText
        ? `${authorText}${year} on ${paper.title}`
        : `${paper.title}${year}`
    })
  const knownCorpusIds = new Set(
    selected
      .map((paper) => paper.corpus_id)
      .filter((id): id is number => id != null)
      .map(String),
  )
  const snippetEntries = citedIds
    .filter((id) => !knownCorpusIds.has(id))
    .map((id) => snippetsByCorpusId.get(id)?.title)
    .filter((title): title is string => !!title)
  const entries = [...paperEntries, ...snippetEntries].slice(0, 4)
  return entries.length > 0
    ? entries.join("; ")
    : "No source paper was attached to this position."
}

function ConversationPanel({
  personas,
  synthesis,
  messages,
  papers,
}: {
  personas: PersonaAgent[]
  synthesis: Synthesis | undefined
  messages: BaselineMessage[]
  papers: Paper[]
}) {
  const activeIds = useBaselineStore((state) => state.activeAgentIds)
  const target = useBaselineStore((state) => state.target)
  const targetSet = useBaselineStore((state) => state.targetSet)
  const debateStage = useAgentBuilderStore((state) => state.pipelineStages.debate)
  const pipelineSteps = useAgentBuilderStore((state) => state.pipelineSteps)
  const activity = getDebateActivity(pipelineSteps)
  const send = useSendBaselineMessage()
  const [draft, setDraft] = useState("")
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  const active = personas.filter((persona) => activeIds.includes(persona.cluster_id))
  const byId = useMemo(
    () => new Map(personas.map((persona) => [String(persona.cluster_id), persona])),
    [personas],
  )
  const papersByCorpusId = useMemo(() => {
    const map = new Map<string, Paper>()
    for (const paper of papers) {
      if (paper.corpus_id != null) map.set(String(paper.corpus_id), paper)
    }
    return map
  }, [papers])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages.length, pendingPrompt, send.isPending])

  const submit = async () => {
    const text = draft.trim()
    if (!text || send.isPending || debateStage !== "complete") return
    const agentIds =
      target === "all"
        ? active.map((persona) => persona.cluster_id)
        : [target]
    if (agentIds.length === 0) return
    setDraft("")
    setPendingPrompt(text)
    try {
      await send.mutateAsync({ message: text, agentIds })
      setPendingPrompt(null)
    } catch {
      setDraft(text)
      setPendingPrompt(null)
    }
  }

  if (debateStage !== "complete") {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center px-5">
        <div className="max-w-md text-center">
          <div className="mx-auto flex size-11 items-center justify-center rounded-full border bg-card">
            {debateStage === "running" ? (
              <FlaskConical className="size-5 animate-pulse text-primary" />
            ) : (
              <MessageSquareText className="size-5 text-muted-foreground" />
            )}
          </div>
          <h2 className="mt-5 font-serif text-2xl tracking-tight">
            {debateStage === "running"
              ? "Researchers are developing hypotheses"
              : "Choose your research team"}
          </h2>
          <p className="mt-2 text-s leading-relaxed text-muted-foreground">
            {debateStage === "running"
              ? activity.detail
              : "Activate two to four perspectives in the researcher panel, then generate hypotheses to begin the discussion."}
          </p>
          {debateStage === "running" && (
            <div className="mx-auto mt-5 w-full max-w-xs" role="status" aria-live="polite">
              <div className="flex items-center justify-between gap-3">
                <TextShimmer className="text-xs">{activity.label}</TextShimmer>
                <span className="shrink-0 font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
                  {activity.index}/{activity.total}
                </span>
              </div>
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-500"
                  style={{ width: `${(activity.index / activity.total) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto flex max-w-3xl flex-col">
          {synthesis?.meta_review && (
            <WorkingHypothesis synthesis={synthesis} />
          )}

          <div className="mt-7 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className={LABEL}>Discussion</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {messages.length === 0 && !pendingPrompt && (
            <div className="py-12 text-center">
              <p className="font-serif text-xl">The research team is ready.</p>
              <p className="mx-auto mt-2 max-w-md text-s leading-relaxed text-muted-foreground">
                Ask for clarification, challenge an assumption, or query one
                researcher directly using the controls below.
              </p>
            </div>
          )}

          <div className="mt-4 flex flex-col gap-1">
            {messages.map((message) => (
              <MessageRow
                key={message.message_id}
                message={message}
                persona={message.agent_id ? byId.get(message.agent_id) : undefined}
                papersByCorpusId={papersByCorpusId}
              />
            ))}
            {pendingPrompt && (
              <>
                <UserMessage content={pendingPrompt} />
                {send.isPending && (
                  <div className="flex gap-3 py-4">
                    <div className="flex -space-x-2">
                      {(target === "all"
                        ? active
                        : active.filter((persona) => persona.cluster_id === target)
                      ).map((persona) => (
                        <AgentAvatar
                          key={persona.cluster_id}
                          clusterId={persona.cluster_id}
                          name={persona.name}
                          className="size-7 border-2 border-background"
                          fallbackClassName="text-[9px]"
                        />
                      ))}
                    </div>
                    <TextShimmer className="text-s">Considering your question...</TextShimmer>
                  </div>
                )}
              </>
            )}
            <div ref={endRef} />
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t bg-background px-4 py-3 sm:px-8 sm:py-4">
        <div className="mx-auto max-w-3xl rounded-lg border bg-card p-2 shadow-sm focus-within:border-ring">
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                submit()
              }
            }}
            placeholder="Ask the research team a follow-up question..."
            className="max-h-32 min-h-14 resize-none border-0 bg-transparent px-2 py-2 text-s shadow-none focus-visible:ring-0 md:text-s"
          />
          <div className="flex flex-wrap items-center gap-1.5 border-t pt-2">
            <span className="mr-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              Ask
            </span>
            <TargetChip active={target === "all"} onClick={() => targetSet("all")}>
              All researchers
            </TargetChip>
            {active.map((persona) => (
              <TargetChip
                key={persona.cluster_id}
                active={target === persona.cluster_id}
                onClick={() => targetSet(persona.cluster_id)}
              >
                {persona.name}
              </TargetChip>
            ))}
            <Button
              size="sm"
              className="ml-auto"
              disabled={!draft.trim() || send.isPending}
              onClick={submit}
              aria-label="Send message"
            >
              <span className="hidden sm:inline">Send</span>
              <Send />
            </Button>
          </div>
        </div>
        {send.error && (
          <p className="mx-auto mt-2 max-w-3xl text-xs text-destructive">
            The researchers could not respond. Your message has been restored;
            try again.
          </p>
        )}
      </div>
    </div>
  )
}

function WorkingHypothesis({ synthesis }: { synthesis: Synthesis }) {
  const meta = synthesis.meta_review
  if (!meta) return null
  return (
    <Collapsible defaultOpen>
      <div className="overflow-hidden rounded-lg border border-primary/25 bg-primary/4">
        <CollapsibleTrigger className="group flex w-full items-center gap-3 px-4 py-3 text-left">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="font-mono text-[10px] uppercase tracking-wide text-primary">
              Working hypothesis
            </span>
            <p className="mt-0.5 line-clamp-2 text-s font-medium leading-snug">
              {meta.hypothesis}
            </p>
          </div>
          <ChevronDown className="size-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="grid gap-px border-t bg-border sm:grid-cols-3">
            <ArtifactField label="Previous work" text={meta.previous_work} />
            <ArtifactField label="Reasoning" text={meta.reasoning} />
            <ArtifactField label="Hypothesis" text={meta.hypothesis} />
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function ArtifactField({ label, text }: { label: string; text: string }) {
  return (
    <div className="bg-background px-4 py-3">
      <span className={LABEL}>{label}</span>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{text}</p>
    </div>
  )
}

function MessageRow({
  message,
  persona,
  papersByCorpusId,
}: {
  message: BaselineMessage
  persona: PersonaAgent | undefined
  papersByCorpusId: Map<string, Paper>
}) {
  if (message.role === "user") return <UserMessage content={message.content} />
  return (
    <div className="flex gap-3 py-4 animate-in fade-in-0 duration-300">
      {persona ? (
        <AgentAvatar
          clusterId={persona.cluster_id}
          name={persona.name}
          className="mt-0.5 size-8 shrink-0"
          fallbackClassName="text-[10px]"
        />
      ) : (
        <Avatar className="mt-0.5 size-8 shrink-0">
          <AvatarFallback>?</AvatarFallback>
        </Avatar>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-s font-medium">{persona?.name ?? "Researcher"}</span>
          {persona && (
            <span className="font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
              {humanizeEnum(persona.reasoning_style)} perspective
            </span>
          )}
        </div>
        <StreamingMarkdown
          text={message.content}
          className="mt-1 text-s leading-relaxed text-muted-foreground [&_p]:my-1 [&_p]:text-s"
        />
        {message.evidence.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-1">
            <span className="mr-1 font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
              Sources
            </span>
            {message.evidence.map((corpusId, index) => {
              const paper = papersByCorpusId.get(corpusId)
              return paper ? (
                <InlineCitation
                  key={`${message.message_id}-${corpusId}`}
                  paper={paper}
                  index={index + 1}
                />
              ) : null
            })}
          </div>
        )}
        {message.rationale && (
          <Collapsible className="mt-2">
            <CollapsibleTrigger className="group flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3 transition-transform group-data-[state=open]:rotate-180" />
              Response rationale
            </CollapsibleTrigger>
            <CollapsibleContent>
              <p className="mt-2 border-l-2 pl-3 text-xs leading-relaxed text-muted-foreground">
                {message.rationale}
              </p>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  )
}

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex gap-3 py-4">
      <Avatar className="mt-0.5 size-8 shrink-0">
        <AvatarFallback className="bg-foreground text-[10px] text-background">
          YOU
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <span className="text-s font-medium">You</span>
        <p className="mt-1 whitespace-pre-wrap text-s leading-relaxed">{content}</p>
      </div>
    </div>
  )
}

function TargetChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
        active
          ? "border-foreground bg-foreground text-background"
          : "bg-background text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  )
}

function PersonaEditor({
  persona,
  onClose,
}: {
  persona: PersonaAgent | undefined
  onClose: () => void
}) {
  const edit = useAgentBuilderStore((state) => state.personaEdited)
  if (!persona) return null
  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-foreground/20 backdrop-blur-sm">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        aria-label="Close researcher editor"
      />
      <aside className="relative flex h-full w-full max-w-md flex-col border-l bg-background shadow-2xl animate-in slide-in-from-right duration-200">
        <div className="flex shrink-0 items-center gap-3 border-b px-5 py-4">
          <AgentAvatar
            clusterId={persona.cluster_id}
            name={persona.name}
            className="size-9"
          />
          <div className="min-w-0 flex-1">
            <span className={LABEL}>Edit researcher</span>
            <p className="truncate text-s font-medium">{persona.name}</p>
          </div>
          <Button size="icon-sm" variant="ghost" onClick={onClose} aria-label="Close">
            <X />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div className="flex flex-col gap-5">
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Name</span>
              <Input
                value={persona.name}
                onChange={(event) =>
                  edit(persona.cluster_id, { name: event.target.value })
                }
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Role</span>
              <Input
                value={persona.role}
                onChange={(event) =>
                  edit(persona.cluster_id, { role: event.target.value })
                }
                placeholder="e.g. HCI Researcher"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Perspective</span>
              <Textarea
                value={persona.perspective || persona.framing}
                onChange={(event) =>
                  edit(persona.cluster_id, { perspective: event.target.value })
                }
                rows={6}
                className="resize-none bg-background text-s md:text-s"
              />
            </label>
            <div className="border-t pt-5">
              <InstructionsEditor
                key={`instructions-${persona.cluster_id}-${persona.instructions.join("\u0000")}`}
                clusterId={persona.cluster_id}
                instructions={persona.instructions}
              />
            </div>
          </div>
        </div>
        <div className="shrink-0 border-t px-5 py-3 text-right">
          <Button onClick={onClose}>Done</Button>
        </div>
      </aside>
    </div>
  )
}
