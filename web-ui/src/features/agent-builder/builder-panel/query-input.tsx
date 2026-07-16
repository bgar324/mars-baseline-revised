"use client"

import { ArrowRight, RotateCcw } from "lucide-react"

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
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useSessionReset } from "@/features/agent-builder/use-session-reset"
import { useCreateQuery } from "@/hooks/use-create-query"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore, type RunMode } from "@/store/agent-builder"

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

const MODE_HINT: Record<RunMode, string> = {
  auto: "Runs the full pipeline automatically.",
  manual: "Choose which researchers debate.",
}

function ModeToggle({ disabled }: { disabled: boolean }) {
  const mode = useAgentBuilderStore((s) => s.mode)
  const modeSet = useAgentBuilderStore((s) => s.modeSet)
  return (
    <div className="flex items-center gap-0.5 rounded-md border p-0.5">
      {(["auto", "manual"] as const).map((m) => (
        <button
          key={m}
          type="button"
          disabled={disabled}
          onClick={() => modeSet(m)}
          className={cn(
            "rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide transition-colors",
            mode === m
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:text-foreground",
            disabled && "cursor-not-allowed opacity-60",
          )}
        >
          {m}
        </button>
      ))}
    </div>
  )
}

export function QueryInput() {
  const draft = useAgentBuilderStore((s) => s.draft)
  const committed = useAgentBuilderStore((s) => s.committed)
  const mode = useAgentBuilderStore((s) => s.mode)
  const draftChanged = useAgentBuilderStore(
    (s) => s.researchProblemDraftChanged,
  )
  const cleared = useSessionReset()

  const { mutate, isPending } = useCreateQuery()

  const isSubmitted = !!committed
  const isDisabled = isPending || isSubmitted
  const canSubmit = draft.trim().length > 0 && !isDisabled

  const submit = () => {
    if (!canSubmit) return
    mutate(draft.trim())
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-2">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className={`${SECTION_LABEL} truncate`}>Research Problem</span>
        {isSubmitted ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="xs">
                <RotateCcw />
                Revise
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle className="tracking-normal">
                  Discard this session?
                </AlertDialogTitle>
                <AlertDialogDescription>
                  Your team and selected researchers will be cleared so you
                  can start a new research query.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep current</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={cleared}>
                  Discard
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : (
          <span className="text-xs text-muted-foreground">Draft</span>
        )}
      </div>

      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate text-[11px] text-muted-foreground">
          {MODE_HINT[mode]}
        </span>
        <ModeToggle disabled={isDisabled} />
      </div>

      <div className="relative">
        <Textarea
          value={draft}
          onChange={(e) => draftChanged(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={isDisabled}
          placeholder="Enter a research query."
          className="h-36 resize-none overflow-y-auto bg-background pr-12 text-s md:text-s"
        />
        <Button
          size="icon-sm"
          variant="outline"
          onClick={submit}
          disabled={!canSubmit}
          aria-label="Submit research problem"
          className="absolute right-2 bottom-2"
        >
          <ArrowRight />
        </Button>
      </div>
    </div>
  )
}
