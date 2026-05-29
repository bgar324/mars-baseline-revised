"use client"

import { useEffect, useMemo, useState } from "react"
import { EditorContent, useEditor } from "@tiptap/react"
import { BubbleMenu } from "@tiptap/react/menus"
import StarterKit from "@tiptap/starter-kit"
import { ChevronDown, ChevronUp, LoaderCircle } from "lucide-react"

import { PaperCard } from "@/components/common/paper-card"
import {
  BasePanel,
  BasePanelBody,
  BasePanelSection,
} from "@/components/layouts/base-panel"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { TextShimmer } from "@/components/ui/text-shimmer"
import { useApplySteer } from "@/hooks/use-apply-steer"
import { usePapers } from "@/hooks/use-papers"
import type { PersonaAgent } from "@/types/persona"
import type { Paper } from "@/types/paper"
import type { Steer, SteerType } from "@/types/debate"
import { initials } from "@/utils/avatar"
import { humanizeEnum } from "@/utils/format"

import { useCycleTurns, useDebateStore, useProposal } from "./debate-store"
import { useBuilderSnapshot } from "./use-builder-snapshot"

const LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

export function SteerPanel({ canvasCycleId }: { canvasCycleId: string }) {
  const builder = useBuilderSnapshot()
  const focalClaim = builder.focalClaim
  const cycle = useCycleTurns(canvasCycleId)
  const locked = cycle?.status === "running" || cycle?.status === "awaiting"
  useDebouncedSteerSync(canvasCycleId, locked)

  return (
    <BasePanel className="rounded-none border-0">
      <BasePanelBody className="gap-5">
        <BasePanelSection title="FOCAL CLAIM">
          {focalClaim ? (
            <p className="text-s">{focalClaim}</p>
          ) : (
            <p className="text-s italic text-muted-foreground">
              No focal claim yet.
            </p>
          )}
        </BasePanelSection>

        <BasePanelSection title="AGENTS">
          <div className="flex flex-col gap-4">
            {builder.team.slice(0, 3).map((persona) => (
              <AgentBlock
                key={persona.cluster_id}
                persona={persona}
                canvasCycleId={canvasCycleId}
                locked={locked}
              />
            ))}
          </div>
        </BasePanelSection>
      </BasePanelBody>
    </BasePanel>
  )
}

function AgentBlock({
  persona,
  canvasCycleId,
  locked,
}: {
  persona: PersonaAgent
  canvasCycleId: string
  locked: boolean
}) {
  const agentId = String(persona.cluster_id)
  const proposal = useProposal(canvasCycleId, agentId)

  return (
    <div className="flex flex-col gap-3 rounded-md border bg-background p-3">
      <div className="flex min-w-0 items-center gap-2">
        <Avatar className="size-7">
          <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">
            {initials(persona.name)}
          </AvatarFallback>
        </Avatar>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-s font-medium">{persona.name}</span>
          <span className="truncate font-mono text-[10px] uppercase text-muted-foreground">
            {humanizeEnum(persona.reasoning_style)}
          </span>
        </div>
      </div>

      <ClaimBlock
        canvasCycleId={canvasCycleId}
        agentId={agentId}
        proposal={proposal}
        locked={locked}
      />

      <ChipField
        canvasCycleId={canvasCycleId}
        agentId={agentId}
        type="emphasize"
        label="Emphasize"
        locked={locked}
      />
      <ChipField
        canvasCycleId={canvasCycleId}
        agentId={agentId}
        type="reframe"
        label="Reframe"
        locked={locked}
      />

      {proposal && proposal.evidence.length > 0 && (
        <EvidenceBlock evidence={proposal.evidence} />
      )}
    </div>
  )
}

function ClaimBlock({
  canvasCycleId,
  agentId,
  proposal,
  locked,
}: {
  canvasCycleId: string
  agentId: string
  proposal: ReturnType<typeof useProposal>
  locked: boolean
}) {
  const content = proposal ? `<p>${escape(proposal.claim)}</p>` : ""

  const editor = useEditor(
    {
      extensions: [StarterKit],
      content,
      editable: false,
      immediatelyRender: false,
    },
    [content],
  )

  useEffect(() => {
    if (!editor) return
    const container = editor.view.dom.closest<HTMLElement>(
      '[data-slot="base-panel-body"]',
    )
    if (!container) return
    const onScroll = () => {
      const { from, empty } = editor.state.selection
      if (!empty) editor.commands.setTextSelection(from)
    }
    container.addEventListener("scroll", onScroll, { passive: true })
    return () => container.removeEventListener("scroll", onScroll)
  }, [editor])

  if (!proposal) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className={LABEL}>Claim</span>
        <div className="flex items-center gap-2 text-s text-muted-foreground">
          <LoaderCircle className="size-3.5 animate-spin" />
          <TextShimmer className="text-s">
            Generating first proposal…
          </TextShimmer>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className={LABEL}>Claim</span>
      <div className="text-s [&_p]:my-0 [&_p]:text-s [&_p]:leading-snug">
        {editor && <EditorContent editor={editor} />}
        {editor && !locked && (
          <BubbleMenu
            editor={editor}
            pluginKey={`steer-${canvasCycleId}-${agentId}`}
            shouldShow={({ state }) => {
              const { from, to, empty } = state.selection
              if (empty || from === to) return false
              return state.doc.textBetween(from, to, " ").trim().length > 0
            }}
            options={{ placement: "top", offset: 8 }}
          >
            <SteerPopover
              onPick={(type) => {
                const { from, to } = editor.state.selection
                const text = editor.state.doc
                  .textBetween(from, to, " ")
                  .trim()
                if (!text) return
                useDebateStore.getState().chipAdded(canvasCycleId, agentId, {
                  type,
                  text,
                  agent_id: agentId,
                  cycle_id: canvasCycleId,
                })
              }}
            />
          </BubbleMenu>
        )}
      </div>
    </div>
  )
}

function EvidenceBlock({
  evidence,
}: {
  evidence: NonNullable<ReturnType<typeof useProposal>>["evidence"]
}) {
  const { data: papers } = usePapers()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const papersById = useMemo(() => {
    const map = new Map<string, Paper>()
    if (papers) for (const p of papers) map.set(p.id, p)
    return map
  }, [papers])
  const cited = evidence
    .map((c) => papersById.get(c.paper_id))
    .filter((p): p is Paper => !!p)
  if (cited.length === 0) return null
  return (
    <Collapsible className="group/evidence flex flex-col gap-1.5">
      <CollapsibleTrigger className="flex w-full cursor-pointer items-center justify-between text-left transition-colors hover:[&_span]:text-foreground">
        <span className={LABEL}>
          Evidence ({cited.length} {cited.length === 1 ? "paper" : "papers"})
        </span>
        <ChevronDown className="size-3.5 shrink-0 text-muted-foreground transition-transform group-data-[state=open]/evidence:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="flex flex-col gap-2 pt-1.5">
          {cited.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              expanded={expandedId === paper.id}
              onToggle={() =>
                setExpandedId((prev) => (prev === paper.id ? null : paper.id))
              }
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function SteerPopover({ onPick }: { onPick: (type: SteerType) => void }) {
  return (
    <div className="flex gap-1 rounded-md border bg-popover p-1 shadow-md">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onPick("emphasize")}
        className="h-7 gap-1 px-2 text-xs"
      >
        <ChevronUp className="size-3" />
        Emphasize
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onPick("reframe")}
        className="h-7 gap-1 px-2 text-xs"
      >
        <ChevronDown className="size-3" />
        Reframe
      </Button>
    </div>
  )
}

function truncate(text: string, max = 40): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function escape(s: string): string {
  return s.replace(/[&<>"']/g, (c) => {
    if (c === "&") return "&amp;"
    if (c === "<") return "&lt;"
    if (c === ">") return "&gt;"
    if (c === '"') return "&quot;"
    return "&#39;"
  })
}

function ChipField({
  canvasCycleId,
  agentId,
  type,
  label,
  locked,
}: {
  canvasCycleId: string
  agentId: string
  type: SteerType
  label: string
  locked: boolean
}) {
  const all = useDebateStore((s) => s.chips[canvasCycleId]?.[agentId])
  const chips = useMemo(
    () => (all ?? []).filter((c) => c.type === type),
    [all, type],
  )
  const [draft, setDraft] = useState("")
  const commitDraft = () => {
    if (locked) return
    const text = draft.trim()
    if (!text) return
    useDebateStore.getState().chipAdded(canvasCycleId, agentId, {
      type,
      text,
      agent_id: agentId,
      cycle_id: canvasCycleId,
    })
    setDraft("")
  }
  const removeChip = (steer: Steer) => {
    if (locked) return
    const all =
      useDebateStore.getState().chips[canvasCycleId]?.[agentId] ?? []
    const idx = all.indexOf(steer)
    if (idx >= 0) {
      useDebateStore.getState().chipRemoved(canvasCycleId, agentId, idx)
    }
  }
  return (
    <section
      className="flex flex-col gap-2"
      aria-disabled={locked || undefined}
    >
      <span className={LABEL}>{label}</span>
      <div className="flex flex-wrap items-center gap-1.5 rounded-md border bg-background px-2 py-1.5 aria-disabled:opacity-60">
        {chips.map((chip, i) => (
          <span
            key={`${chip.text}-${i}`}
            title={chip.text}
            className="inline-flex max-w-full items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs"
          >
            <span className="truncate">{truncate(chip.text)}</span>
            <button
              type="button"
              onClick={() => removeChip(chip)}
              disabled={locked}
              className="text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:hover:text-muted-foreground"
              aria-label={`Remove ${chip.text}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              commitDraft()
            }
          }}
          onBlur={commitDraft}
          disabled={locked}
          placeholder={locked ? "" : "Type or select text above…"}
          className="min-w-32 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
        />
      </div>
    </section>
  )
}

function useDebouncedSteerSync(canvasCycleId: string, locked: boolean) {
  const chipsByAgent = useDebateStore((s) => s.chips[canvasCycleId])
  const apply = useApplySteer()
  useEffect(() => {
    if (locked) return
    const { debateId, canvasToBackend, cyclesByBackendId } =
      useDebateStore.getState()
    const backendCycleId = canvasToBackend[canvasCycleId]
    if (!debateId || !backendCycleId) return
    if (!chipsByAgent) return
    const all: Steer[] = Object.values(chipsByAgent).flat()
    const serverSteers = cyclesByBackendId[backendCycleId]?.steers ?? []
    if (all.length === 0 && serverSteers.length === 0) return
    const handle = setTimeout(() => {
      const status =
        useDebateStore.getState().cyclesByBackendId[backendCycleId]?.status
      if (status === "running" || status === "awaiting") return
      apply.mutate({ debateId, backendCycleId, steers: all })
    }, 600)
    return () => clearTimeout(handle)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chipsByAgent, canvasCycleId, locked])
}
