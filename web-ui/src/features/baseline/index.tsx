"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import {
  BookOpen,
  Check,
  ChevronDown,
  Download,
  ExternalLink,
  FlaskConical,
  Info,
  LoaderCircle,
  Menu,
  MessageSquareText,
  Plus,
  RotateCcw,
  Search,
  Send,
  UsersRound,
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
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { InstructionsEditor } from "@/features/agent-builder/context-panel/instructions-editor"
import { useBaselineChat, useSendBaselineMessage } from "@/hooks/use-baseline-chat"
import { useBaselineExport } from "@/hooks/use-baseline-export"
import { useDebate } from "@/hooks/use-debate"
import { useHypotheses } from "@/hooks/use-hypotheses"
import {
  PAPER_SEARCH_PAGE_SIZE,
  usePaperSearch,
} from "@/hooks/use-paper-search"
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

const LABEL =
  "text-[11px] font-medium uppercase tracking-normal text-muted-foreground"

function createManualPersona(clusterId: number): PersonaAgent {
  return {
    cluster_id: clusterId,
    name: "",
    role: "",
    perspective: "",
    framing: "",
    background: "Manually defined research perspective.",
    methods_summary: "Selected literature and user-defined expertise.",
    evidence_relation: "direct",
    reasoning_style: "theoretical",
    evaluation_lens: "construct_validity",
    references: [],
    instructions: [
      "Argue from the stated perspective.",
      "Ground claims in the selected papers.",
      "State uncertainty and important limitations.",
    ],
    constraints: null,
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

// Per-agent copy for the live turn phase streamed via `agent.thinking`, so each
// researcher card narrates what that specific researcher is doing right now.
const LIVE_PHASE_LABEL: Record<string, string> = {
  proposal: "Drafting an opening position",
  rebuttal: "Responding to the other researchers",
  refinement: "Refining the argument",
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

function useBaselineReset() {
  const queryClient = useQueryClient()
  const resetBaseline = useBaselineStore((state) => state.reset)
  const clearBuilder = useAgentBuilderStore(
    (state) => state.researchProblemCleared,
  )
  const conditionSet = useAgentBuilderStore((state) => state.studyConditionSet)
  return () => {
    resetBaseline()
    clearBuilder()
    conditionSet("baseline")
    queryClient.clear()
  }
}

function AppHeader({
  testMode,
  left,
  children,
}: {
  testMode?: boolean
  left?: React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <header className="relative flex h-12 shrink-0 items-center border-b bg-background px-3 sm:px-4">
      <div className="flex min-w-0 items-center gap-2">
        {left}
        <span className="shrink-0 text-l font-semibold tracking-tight">
          MARS
        </span>
        <HoverCard openDelay={80} closeDelay={80}>
          <HoverCardTrigger asChild>
            <button
              type="button"
              aria-label="About the MARS baseline"
              className="rounded-full text-muted-foreground/55 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            >
              <Info className="size-3.5" />
            </button>
          </HoverCardTrigger>
          <HoverCardContent align="start" className="w-80">
            <p className="text-s font-medium">Manual research baseline</p>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
              Write a research question, build two to four perspectives, and
              attach papers from Semantic Scholar. Nothing is submitted until
              you generate hypotheses.
            </p>
          </HoverCardContent>
        </HoverCard>
      </div>
      {testMode && (
        <span className="pointer-events-none absolute left-1/2 hidden -translate-x-1/2 items-center rounded-full border border-primary/25 bg-primary/5 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary sm:inline-flex">
          Test mode
        </span>
      )}
      {children && (
        <div className="ml-auto flex items-center gap-2">{children}</div>
      )}
    </header>
  )
}

export function BaselineWorkspace() {
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const condition = useAgentBuilderStore((state) => state.studyCondition)
  const isBaseline = condition === "baseline"
  const clearBuilder = useAgentBuilderStore(
    (state) => state.researchProblemCleared,
  )
  const conditionSet = useAgentBuilderStore((state) => state.studyConditionSet)
  const resetBaseline = useBaselineStore((state) => state.reset)

  useEffect(() => {
    if (isBaseline) return
    clearBuilder()
    resetBaseline()
    conditionSet("baseline")
  }, [clearBuilder, conditionSet, isBaseline, resetBaseline])

  useQueryEvents(isBaseline ? queryId : null)

  if (!isBaseline) return null
  return <DiscussionWorkspace />
}

function DiscussionWorkspace() {
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const question = useAgentBuilderStore((state) => state.draft)
  const questionChanged = useAgentBuilderStore(
    (state) => state.researchProblemDraftChanged,
  )
  const { data: debate } = useDebate()
  const { data: synthesis } = useHypotheses()
  const { data: conversation } = useBaselineChat()
  const manualPersonas = useBaselineStore((state) => state.manualPersonas)
  const manualPapers = useBaselineStore((state) => state.manualPapers)
  const manualPersonaAdded = useBaselineStore(
    (state) => state.manualPersonaAdded,
  )
  const manualPersonaEdited = useBaselineStore(
    (state) => state.manualPersonaEdited,
  )
  const manualPersonaRemoved = useBaselineStore(
    (state) => state.manualPersonaRemoved,
  )
  const exportSession = useBaselineExport()
  const testMode = useBaselineStore((state) => state.testMode)
  const reset = useBaselineReset()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [newPerspectiveId, setNewPerspectiveId] = useState<number | null>(null)

  const addPerspective = () => {
    const clusterId =
      Math.max(999, ...manualPersonas.map((persona) => persona.cluster_id)) + 1
    manualPersonaAdded(createManualPersona(clusterId))
    setNewPerspectiveId(clusterId)
    setEditingId(clusterId)
  }

  const editPersona = (clusterId: number, patch: Partial<PersonaAgent>) => {
    manualPersonaEdited(clusterId, patch)
  }

  const closeEditor = (save = false) => {
    if (!save && editingId === newPerspectiveId && editingId != null) {
      manualPersonaRemoved(editingId)
    }
    setEditingId(null)
    setNewPerspectiveId(null)
  }

  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-background">
      <AppHeader
        testMode={testMode}
        left={
          <Button
            size="icon-xs"
            variant="ghost"
            className="md:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open researcher panel"
          >
            <Menu />
          </Button>
        }
      >
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
      </AppHeader>

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
            personas={manualPersonas}
            turns={debate?.cycle?.turns ?? []}
            evidence={debate?.cycle?.evidence ?? {}}
            papers={manualPapers}
            onEdit={setEditingId}
            onAdd={addPerspective}
          />
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div className="shrink-0 border-b px-4 py-2.5 sm:px-8">
            <div className="mx-auto max-w-3xl">
              <Textarea
                value={question}
                onChange={(event) => questionChanged(event.target.value)}
                disabled={!!queryId}
                aria-label="Research question"
                placeholder="Enter the research question your team should examine…"
                className="min-h-10 resize-none border-0 bg-transparent px-0 py-1 text-s font-medium leading-relaxed shadow-none focus-visible:border-0 focus-visible:ring-0 disabled:cursor-default disabled:opacity-100"
              />
            </div>
          </div>
          <ConversationPanel
            personas={manualPersonas}
            synthesis={synthesis}
            messages={conversation?.messages ?? []}
            papers={manualPapers}
            question={question}
          />
        </main>
      </div>

      {editingId != null && (
        <PersonaEditor
          persona={manualPersonas.find((item) => item.cluster_id === editingId)}
          papers={manualPapers}
          isNew={editingId === newPerspectiveId}
          isManual
          onEdit={editPersona}
          onCancel={() => closeEditor(false)}
          onDone={() => closeEditor(true)}
          onRemove={() => {
            manualPersonaRemoved(editingId)
            closeEditor(true)
          }}
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
  onAdd,
}: {
  personas: PersonaAgent[]
  turns: AgentTurn[]
  evidence: Record<string, EvidenceSet>
  papers: Paper[]
  onEdit: (id: number) => void
  onAdd: () => void
}) {
  const activeIds = useBaselineStore((state) => state.activeAgentIds)
  const activeAgentsSet = useBaselineStore((state) => state.activeAgentsSet)
  const target = useBaselineStore((state) => state.target)
  const targetSet = useBaselineStore((state) => state.targetSet)
  const debateStage = useAgentBuilderStore((state) => state.pipelineStages.debate)
  const pipelineSteps = useAgentBuilderStore((state) => state.pipelineSteps)
  const thinkingAgents = useAgentBuilderStore((state) => state.thinkingAgents)
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

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b px-4 py-3">
        <div className="flex items-end justify-between gap-2">
          <div>
            <div className="flex items-center gap-1.5">
              <p className="text-s font-medium">Research team</p>
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                disabled={locked}
                onClick={onAdd}
                aria-label="Add perspective"
                title="Add perspective"
                className="-my-1 text-muted-foreground hover:text-foreground"
              >
                <Plus />
              </Button>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Build and select 2–4 perspectives for the discussion.
            </p>
          </div>
          <span className="text-[10px] text-muted-foreground">
            {activeIds.length}/4
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {personas.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed bg-background px-5 text-center">
            <div className="flex size-9 items-center justify-center rounded-full border bg-muted/25 text-muted-foreground">
              <UsersRound className="size-4" />
            </div>
            <p className="mt-3 text-s font-medium">Build your research team</p>
            <p className="mt-1 max-w-52 text-xs leading-relaxed text-muted-foreground">
              Add each perspective manually, then ground it in papers you choose.
            </p>
            <Button className="mt-4" variant="shine" onClick={onAdd}>
              <Plus />
              Add first perspective
            </Button>
          </div>
        ) : (
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
                  livePhase={thinkingAgents[String(persona.cluster_id)]}
                  proposal={proposal}
                  activity={activity}
                  evidenceCount={agentEvidence?.snippets.length ?? 0}
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
        )}
      </div>
    </div>
  )
}

function ResearcherCard({
  persona,
  active,
  locked,
  loading,
  livePhase,
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
  livePhase: string | undefined
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
          <span className="text-[9px] uppercase tracking-wide text-muted-foreground">
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
            <div className={cn(proposal && "mb-3 border-b pb-3")}>
              <div className="min-w-0">
                <TextShimmer className="text-xs">
                  {(livePhase && LIVE_PHASE_LABEL[livePhase]) ||
                    activity.cardLabel}
                </TextShimmer>
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                  {evidenceCount > 0
                    ? `Reviewing ${persona.references.length} attached paper${persona.references.length === 1 ? "" : "s"}; ${evidenceCount} relevant evidence passage${evidenceCount === 1 ? "" : "s"} selected.`
                    : persona.references.length > 0
                      ? `Searching ${persona.references.length} attached paper${persona.references.length === 1 ? "" : "s"} for the most relevant evidence.`
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
    <div className="rounded-md border bg-background px-3 py-2.5">
      <span
        className={cn(
          "text-[9px] uppercase tracking-wide",
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
  question,
}: {
  personas: PersonaAgent[]
  synthesis: Synthesis | undefined
  messages: BaselineMessage[]
  papers: Paper[]
  question: string
}) {
  const activeIds = useBaselineStore((state) => state.activeAgentIds)
  const target = useBaselineStore((state) => state.target)
  const targetSet = useBaselineStore((state) => state.targetSet)
  const debateStage = useAgentBuilderStore((state) => state.pipelineStages.debate)
  const debateError = useAgentBuilderStore((state) => state.stageErrors.debate)
  const pipelineSteps = useAgentBuilderStore((state) => state.pipelineSteps)
  const activity = getDebateActivity(pipelineSteps)
  const runDebate = useRunDebate()
  const send = useSendBaselineMessage()
  const [draft, setDraft] = useState("")
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  const active = personas.filter((persona) => activeIds.includes(persona.cluster_id))
  const canGenerate =
    question.trim().length > 0 &&
    active.length >= 2 &&
    active.length <= 4 &&
    debateStage !== "running" &&
    !runDebate.isPending
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
          <h2 className="mt-5 text-2xl font-semibold tracking-tight">
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
                <span className="shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground">
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
          {debateStage !== "running" && (
            <div className="mt-6">
              <Button
                variant="shine"
                disabled={!canGenerate}
                onClick={() =>
                  runDebate.mutate({
                    personas: active,
                    question: question.trim(),
                  })
                }
              >
                {runDebate.isPending
                  ? "Starting discussion…"
                  : "Generate hypotheses"}
              </Button>
              {(runDebate.error || debateError) && (
                <p className="mt-3 text-xs text-destructive">
                  {debateError ?? "Could not generate hypotheses."}
                </p>
              )}
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
              <p className="text-xl font-semibold">The research team is ready.</p>
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
            <span className="mr-1 text-[10px] uppercase tracking-wide text-muted-foreground">
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
          <div className="min-w-0 flex-1">
            <span className="text-[10px] uppercase tracking-wide text-primary">
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
            <span className="text-[9px] uppercase tracking-wide text-muted-foreground">
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
            <span className="mr-1 text-[9px] uppercase tracking-wide text-muted-foreground">
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
            <CollapsibleTrigger className="group flex items-center gap-1 text-[10px] uppercase tracking-wide text-muted-foreground hover:text-foreground">
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
  papers,
  isNew,
  isManual,
  onEdit,
  onCancel,
  onDone,
  onRemove,
}: {
  persona: PersonaAgent | undefined
  papers: Paper[]
  isNew: boolean
  isManual: boolean
  onEdit: (clusterId: number, patch: Partial<PersonaAgent>) => void
  onCancel: () => void
  onDone: () => void
  onRemove: () => void
}) {
  const [paperQuery, setPaperQuery] = useState("")
  const [paperPage, setPaperPage] = useState(1)
  const paperSearchTopRef = useRef<HTMLFormElement | null>(null)
  const searchPapers = usePaperSearch()
  const manualPapersAdded = useBaselineStore(
    (state) => state.manualPapersAdded,
  )
  if (!persona) return null

  const selectedIds = new Set(persona.references)
  const searchResultCount = searchPapers.data?.length ?? 0
  const pageStart = (paperPage - 1) * PAPER_SEARCH_PAGE_SIZE
  const pageResults = (searchPapers.data ?? []).slice(
    pageStart,
    pageStart + PAPER_SEARCH_PAGE_SIZE,
  )
  const searchResultIds = new Set(
    (searchPapers.data ?? []).map((paper) => paper.id),
  )
  const selectedPapers = persona.references
    .map((id) => papers.find((paper) => paper.id === id))
    .filter(
      (paper): paper is Paper => !!paper && !searchResultIds.has(paper.id),
    )
  const allSearchResultsAttached =
    searchResultIds.size > 0 &&
    [...searchResultIds].every((id) => selectedIds.has(id))
  const complete =
    persona.name.trim().length > 0 &&
    persona.role.trim().length > 0 &&
    (persona.perspective || persona.framing).trim().length > 0

  const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const query = paperQuery.trim()
    if (query.length >= 2) {
      setPaperPage(1)
      void searchPapers.mutate(query)
    }
  }

  const togglePaper = (paper: Paper) => {
    const references = selectedIds.has(paper.id)
      ? persona.references.filter((id) => id !== paper.id)
      : [...persona.references, paper.id]
    if (!selectedIds.has(paper.id)) manualPapersAdded([paper])
    onEdit(persona.cluster_id, { references })
  }

  const attachAllPapers = () => {
    const results = searchPapers.data ?? []
    if (results.length === 0 || allSearchResultsAttached) return
    manualPapersAdded(results)
    onEdit(persona.cluster_id, {
      references: [
        ...new Set([...persona.references, ...results.map((paper) => paper.id)]),
      ],
    })
  }

  const showPaperPage = (page: number) => {
    setPaperPage(page)
    requestAnimationFrame(() => {
      paperSearchTopRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    })
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-foreground/20 backdrop-blur-sm">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onCancel}
        aria-label="Close researcher editor"
      />
      <aside className="relative flex h-full w-full max-w-lg flex-col border-l bg-background shadow-2xl animate-in slide-in-from-right duration-200">
        <div className="flex shrink-0 items-center gap-3 border-b px-5 py-4">
          <AgentAvatar
            clusterId={persona.cluster_id}
            name={persona.name || "New perspective"}
            className="size-9"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-s font-medium">
              {persona.name || "Untitled perspective"}
            </p>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div className="flex flex-col gap-5">
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Name</span>
              <Input
                value={persona.name}
                onChange={(event) =>
                  onEdit(persona.cluster_id, { name: event.target.value })
                }
                placeholder="e.g. Dr. Maya Chen"
                autoFocus={isNew}
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Role</span>
              <Input
                value={persona.role}
                onChange={(event) =>
                  onEdit(persona.cluster_id, { role: event.target.value })
                }
                placeholder="e.g. HCI Researcher"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={LABEL}>Perspective</span>
              <Textarea
                value={persona.perspective || persona.framing}
                onChange={(event) => {
                  const perspective = event.target.value
                  onEdit(persona.cluster_id, {
                    perspective,
                    framing: perspective,
                  })
                }}
                rows={6}
                className="resize-none bg-background text-s md:text-s"
                placeholder="Describe the lens this researcher brings, what they focus on, and the concerns or outcomes they prioritize."
              />
            </label>

            <section className="border-t pt-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className={LABEL}>Source papers</span>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Search Semantic Scholar and attach the papers this
                    perspective should reason from.
                  </p>
                </div>
                <span className="shrink-0 rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground">
                  {persona.references.length} attached
                </span>
              </div>

              <form
                ref={paperSearchTopRef}
                onSubmit={submitSearch}
                className="mt-3 flex scroll-mt-5 gap-2"
              >
                <div className="relative min-w-0 flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={paperQuery}
                    onChange={(event) => setPaperQuery(event.target.value)}
                    placeholder="Search by topic, title, or author"
                    className="pl-9"
                  />
                </div>
                <Button
                  type="submit"
                  variant="outline"
                  disabled={paperQuery.trim().length < 2 || searchPapers.isPending}
                >
                  {searchPapers.isPending ? (
                    <LoaderCircle className="animate-spin" />
                  ) : (
                    <Search />
                  )}
                  Search
                </Button>
              </form>

              {selectedPapers.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    Attached literature
                  </p>
                  <div className="space-y-2">
                    {selectedPapers.map((paper) => (
                      <PaperChoice
                        key={`selected-${paper.id}`}
                        paper={paper}
                        selected
                        onToggle={() => togglePaper(paper)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {searchPapers.data && (
                <div className="mt-4">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Search results
                    </p>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">
                        {searchResultCount} result
                        {searchResultCount === 1 ? "" : "s"}
                      </span>
                      <Button
                        type="button"
                        variant="outline"
                        size="xs"
                        disabled={allSearchResultsAttached}
                        onClick={attachAllPapers}
                      >
                        {allSearchResultsAttached ? "All attached" : "Attach all"}
                      </Button>
                    </div>
                  </div>
                  {pageResults.length > 0 ? (
                    <div className="space-y-2">
                      {pageResults.map((paper) => (
                        <PaperChoice
                          key={`result-${paper.id}`}
                          paper={paper}
                          selected={selectedIds.has(paper.id)}
                          onToggle={() => togglePaper(paper)}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="rounded-lg border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
                      No papers matched this search.
                    </p>
                  )}

                  {searchResultCount > 0 && (
                    <div className="mt-3 flex items-center justify-between gap-3 border-t pt-3">
                      <span className="text-[10px] text-muted-foreground">
                        Page {paperPage} of 5
                      </span>
                      <div
                        className="flex items-center gap-1"
                        aria-label="Paper result pages"
                      >
                        {Array.from({ length: 5 }, (_, index) => {
                          const page = index + 1
                          const loaded =
                            index * PAPER_SEARCH_PAGE_SIZE < searchResultCount
                          const active = page === paperPage
                          return (
                            <button
                              key={page}
                              type="button"
                              disabled={!loaded}
                              onClick={() => showPaperPage(page)}
                              aria-label={`Show paper results page ${page}`}
                              aria-current={active ? "page" : undefined}
                              className={cn(
                                "flex size-7 items-center justify-center rounded-md border text-[10px] transition-colors",
                                active
                                  ? "border-foreground bg-foreground text-background"
                                  : "bg-background text-muted-foreground hover:text-foreground",
                                !loaded && "cursor-wait opacity-35",
                              )}
                            >
                              {page}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {searchPapers.error && (
                <p className="mt-3 text-xs text-destructive">
                  Could not search Semantic Scholar. Try again in a moment.
                </p>
              )}
            </section>

            {!isManual && (
              <div className="border-t pt-5">
                <InstructionsEditor
                  key={`instructions-${persona.cluster_id}-${persona.instructions.join("\u0000")}`}
                  clusterId={persona.cluster_id}
                  instructions={persona.instructions}
                />
              </div>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center border-t px-5 py-3">
          {isManual && !isNew && (
            <Button
              variant="destructive"
              onClick={onRemove}
            >
              Remove perspective
            </Button>
          )}
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" onClick={onCancel}>
              {isNew ? "Cancel" : "Close"}
            </Button>
            <Button onClick={onDone} disabled={!complete}>
              {isNew ? "Add perspective" : "Done"}
            </Button>
          </div>
        </div>
      </aside>
    </div>
  )
}

function PaperChoice({
  paper,
  selected,
  onToggle,
}: {
  paper: Paper
  selected: boolean
  onToggle: () => void
}) {
  const authors = paper.authors
    .slice(0, 2)
    .map((author) => author.name)
    .join(", ")
  const meta = [authors, paper.year, paper.venue].filter(Boolean).join(" · ")

  return (
    <div
      className={cn(
        "group rounded-lg border px-3 py-3 transition-colors",
        selected ? "border-primary/40 bg-primary/[0.035]" : "hover:bg-muted/25",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border",
            selected
              ? "border-primary bg-primary text-primary-foreground"
              : "bg-background text-muted-foreground",
          )}
        >
          {selected ? <Check className="size-3.5" /> : <BookOpen className="size-3.5" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 text-xs font-medium leading-snug">
            {paper.title}
          </p>
          {meta && (
            <p className="mt-1 truncate text-[10px] text-muted-foreground">
              {meta}
            </p>
          )}
          {paper.tldr && (
            <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
              {paper.tldr}
            </p>
          )}
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={onToggle}
              className="text-[10px] font-medium text-primary hover:underline"
            >
              {selected ? "Remove" : "Attach paper"}
            </button>
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
              >
                View paper
                <ExternalLink className="size-2.5" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
