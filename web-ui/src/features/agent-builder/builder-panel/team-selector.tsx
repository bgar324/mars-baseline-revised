"use client"

import { Fragment, useState } from "react"
import { Plus } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox"
import { Field } from "@/components/ui/field"
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item"
import { useChainReset } from "@/features/agent-builder/use-session-reset"
import { useChainStore } from "@/features/hypo-canvas/chain-store"
import { usePersonas } from "@/hooks/use-personas"
import { TEAM_SIZE_MAX, useAgentBuilderStore } from "@/store/agent-builder"
import type { PersonaAgent } from "@/types/persona"
import { initials } from "@/utils/avatar"
import { humanizeEnum } from "@/utils/format"

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

type Pending =
  | { kind: "add" }
  | { kind: "remove"; clusterId: number }
  | null

export function TeamSelector() {
  const team = useAgentBuilderStore((s) => s.team)
  const teamAdded = useAgentBuilderStore((s) => s.teamMemberAdded)
  const teamRemoved = useAgentBuilderStore((s) => s.teamMemberRemoved)
  const locked = useChainStore((s) => s.cycles.length > 0)
  const resetChain = useChainReset()

  const { data: personas } = usePersonas()
  const anchor = useComboboxAnchor()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState<Pending>(null)

  const atMax = team.length >= TEAM_SIZE_MAX
  const canAdd = !atMax && !!personas?.length

  const onPlusClick = () => {
    if (locked) {
      setPending({ kind: "add" })
      return
    }
    setOpen(true)
  }

  const confirmRestart = () => {
    if (!pending) return
    const next = pending
    resetChain()
    setPending(null)
    if (next.kind === "add") {
      setOpen(true)
    } else {
      teamRemoved(next.clusterId)
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className={SECTION_LABEL}>
          Team Members ({team.length} / {TEAM_SIZE_MAX})
        </span>
        <Button
          size="icon-xs"
          variant="outline"
          aria-label="Add team member"
          onClick={onPlusClick}
          disabled={!canAdd}
          className="rounded-full"
        >
          <Plus />
        </Button>
      </div>

      {team.length === 0 && !personas?.length ? (
        <p className="text-s text-muted-foreground">No members yet.</p>
      ) : (
        <Field>
          <Combobox
            multiple
            open={open}
            onOpenChange={setOpen}
            items={personas ?? []}
            itemToStringValue={(p: PersonaAgent) => p.name}
            value={team}
            onValueChange={(next: PersonaAgent[]) => {
              const added = next.find(
                (p) => !team.some((t) => t.cluster_id === p.cluster_id),
              )
              const removed = team.find(
                (p) => !next.some((n) => n.cluster_id === p.cluster_id),
              )
              if (locked) {
                if (removed) {
                  setPending({ kind: "remove", clusterId: removed.cluster_id })
                }
                return
              }
              if (added && !atMax) teamAdded(added)
              if (removed) teamRemoved(removed.cluster_id)
            }}
          >
            <ComboboxChips
              ref={anchor}
              className="border-none bg-transparent p-0 shadow-none ring-0 focus-within:ring-0 has-data-[slot=combobox-chip]:px-0"
            >
              <ComboboxValue>
                {(selected: PersonaAgent[]) => (
                  <Fragment>
                    {selected.map((member) => (
                      <ComboboxChip
                        key={member.cluster_id}
                        showRemove
                        className="bg-background rounded-full inline-flex h-auto max-w-full items-center gap-1 overflow-hidden border py-0.5 pl-1 shadow-xs **:data-[slot=combobox-chip-remove]:mr-0.5 **:data-[slot=combobox-chip-remove]:bg-transparent"
                      >
                        <Avatar className="size-4 shrink-0">
                          <AvatarFallback className="bg-muted pt-px text-[8px] leading-none text-muted-foreground">
                            {initials(member.name)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="min-w-0 truncate">{member.name}</span>
                      </ComboboxChip>
                    ))}
                    <ComboboxChipsInput
                      placeholder={
                        atMax || locked
                          ? ""
                          : team.length === 0
                            ? "Add team members..."
                            : ""
                      }
                      disabled={atMax || locked}
                      className="bg-transparent text-s md:text-s"
                    />
                  </Fragment>
                )}
              </ComboboxValue>
            </ComboboxChips>
            <ComboboxContent
              anchor={anchor}
              className="w-80 max-w-[calc(100vw-2rem)]"
            >
              <ComboboxEmpty>No members found.</ComboboxEmpty>
              <ComboboxList>
                {(member: PersonaAgent) => (
                  <ComboboxItem key={member.cluster_id} value={member}>
                    <Item size="xs" className="flex-nowrap p-0">
                      <Avatar className="size-6">
                        <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">
                          {initials(member.name)}
                        </AvatarFallback>
                      </Avatar>
                      <ItemContent className="min-w-0">
                        <ItemTitle className="truncate text-s font-medium">
                          {member.name}
                        </ItemTitle>
                        <ItemDescription className="truncate font-mono text-[10px] uppercase">
                          {humanizeEnum(member.reasoning_style)}
                        </ItemDescription>
                      </ItemContent>
                    </Item>
                  </ComboboxItem>
                )}
              </ComboboxList>
            </ComboboxContent>
          </Combobox>
        </Field>
      )}

      <AlertDialog
        open={pending !== null}
        onOpenChange={(next) => {
          if (!next) setPending(null)
        }}
      >
        <AlertDialogContent
          className="h-fit!"
          style={{
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            margin: "auto",
            transform: "none",
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle className="tracking-normal">
              Restart the team?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Your current canvas progress (steer / debate cycles) will be
              cleared so you can adjust the team. The research problem stays.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep current</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmRestart}>
              Restart
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
