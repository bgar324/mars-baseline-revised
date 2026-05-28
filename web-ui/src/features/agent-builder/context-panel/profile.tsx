"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { useAgentBuilderStore } from "@/store/agent-builder"
import {
  EVALUATION_LENS_DESCRIPTIONS,
  EvaluationLensSchema,
  REASONING_STYLE_DESCRIPTIONS,
  ReasoningStyleSchema,
  type EvaluationLens,
  type PersonaAgent,
  type ReasoningStyle,
} from "@/types/persona"
import { humanizeEnum } from "@/utils/format"

import { InstructionsEditor } from "./instructions-editor"

const FIELD_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

const REASONING_STYLES = ReasoningStyleSchema.options
const EVALUATION_LENSES = EvaluationLensSchema.options

export function Profile({ persona }: { persona: PersonaAgent }) {
  const edit = useAgentBuilderStore((s) => s.personaEdited)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <span className={FIELD_LABEL}>Reasoning style</span>
        <Select
          value={persona.reasoning_style}
          onValueChange={(v) =>
            edit(persona.cluster_id, { reasoning_style: v as ReasoningStyle })
          }
        >
          <SelectTrigger className="h-9 w-full text-s [&_span.font-medium]:text-s! [&_span.text-muted-foreground]:hidden">
            <SelectValue />
          </SelectTrigger>
          <SelectContent position="popper">
            {REASONING_STYLES.map((s) => (
              <SelectItem key={s} value={s}>
                <div className="flex flex-col items-start gap-px">
                  <span className="text-s font-medium">
                    {humanizeEnum(s)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {REASONING_STYLE_DESCRIPTIONS[s]}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <span className={FIELD_LABEL}>Evaluation lens</span>
        <Select
          value={persona.evaluation_lens}
          onValueChange={(v) =>
            edit(persona.cluster_id, { evaluation_lens: v as EvaluationLens })
          }
        >
          <SelectTrigger className="h-9 w-full text-s [&_span.font-medium]:text-s! [&_span.text-muted-foreground]:hidden">
            <SelectValue />
          </SelectTrigger>
          <SelectContent position="popper">
            {EVALUATION_LENSES.map((s) => (
              <SelectItem key={s} value={s}>
                <div className="flex flex-col items-start gap-px">
                  <span className="text-s font-medium">
                    {humanizeEnum(s)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {EVALUATION_LENS_DESCRIPTIONS[s]}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Separator />

      <BlurField
        label="Framing"
        value={persona.framing}
        rows={3}
        onCommit={(v) => edit(persona.cluster_id, { framing: v })}
      />

      <BlurField
        label="Background"
        value={persona.background}
        rows={4}
        onCommit={(v) => edit(persona.cluster_id, { background: v })}
      />

      <Separator />

      <InstructionsEditor
        clusterId={persona.cluster_id}
        instructions={persona.instructions}
      />

      <Separator />

      <ConstraintsField persona={persona} />
    </div>
  )
}

function BlurField({
  label,
  value,
  rows,
  onCommit,
}: {
  label: string
  value: string
  rows: number
  onCommit: (v: string) => void
}) {
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  return (
    <div className="flex flex-col gap-2">
      <span className={FIELD_LABEL}>{label}</span>
      <Textarea
        value={draft}
        rows={rows}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          if (draft !== value) onCommit(draft)
        }}
        className="resize-none bg-background text-s md:text-s"
      />
    </div>
  )
}

function ConstraintsField({ persona }: { persona: PersonaAgent }) {
  const edit = useAgentBuilderStore((s) => s.personaEdited)
  const [draft, setDraft] = useState(persona.constraints ?? "")

  useEffect(() => {
    setDraft(persona.constraints ?? "")
  }, [persona.cluster_id, persona.constraints])

  const commit = () => {
    const next = draft.trim() ? draft : null
    if (next === persona.constraints) return
    edit(persona.cluster_id, { constraints: next })
  }

  const clear = () => {
    setDraft("")
    if (persona.constraints !== null) {
      edit(persona.cluster_id, { constraints: null })
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className={FIELD_LABEL}>Constraints</span>
        {persona.constraints != null && (
          <Button
            type="button"
            size="xs"
            variant="ghost"
            className="text-muted-foreground"
            onClick={clear}
          >
            clear
          </Button>
        )}
      </div>
      <Textarea
        value={draft}
        rows={3}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        placeholder="No constraints set."
        className="resize-none bg-background text-s md:text-s"
      />
    </div>
  )
}
