"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import { restrictToVerticalAxis } from "@dnd-kit/modifiers"
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical, Plus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useAgentBuilderStore } from "@/store/agent-builder"

const MIN_INSTRUCTIONS = 3
const MAX_INSTRUCTIONS = 5

const FIELD_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

type Row = { id: string; text: string }

export function InstructionsEditor({
  clusterId,
  instructions,
}: {
  clusterId: number
  instructions: string[]
}) {
  const personaEdited = useAgentBuilderStore((s) => s.personaEdited)
  const counterRef = useRef(0)
  const newRowIdRef = useRef<string | null>(null)

  const [rows, setRows] = useState<Row[]>(() =>
    instructions.map((text, i) => ({ id: `i-${i}`, text })),
  )

  useEffect(() => {
    const sameLength = rows.length === instructions.length
    const sameText = sameLength && rows.every((r, i) => r.text === instructions[i])
    if (sameText) return
    setRows(instructions.map((text, i) => ({ id: `i-${i}`, text })))
  }, [instructions]) // eslint-disable-line react-hooks/exhaustive-deps

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  )

  const commit = (next: Row[]) => {
    setRows(next)
    personaEdited(clusterId, { instructions: next.map((r) => r.text) })
  }

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const oldIdx = rows.findIndex((r) => r.id === active.id)
    const newIdx = rows.findIndex((r) => r.id === over.id)
    if (oldIdx === -1 || newIdx === -1) return
    commit(arrayMove(rows, oldIdx, newIdx))
  }

  const updateAt = (idx: number, text: string) => {
    if (rows[idx]?.text === text) return
    const next = rows.map((r, i) => (i === idx ? { ...r, text } : r))
    commit(next)
  }

  const deleteAt = (idx: number) => {
    if (rows.length <= MIN_INSTRUCTIONS) return
    commit(rows.filter((_, i) => i !== idx))
  }

  const addRow = () => {
    if (rows.length >= MAX_INSTRUCTIONS) return
    counterRef.current += 1
    const id = `n-${counterRef.current}`
    newRowIdRef.current = id
    commit([...rows, { id, text: "" }])
  }

  const ids = useMemo(() => rows.map((r) => r.id), [rows])
  const canDelete = rows.length > MIN_INSTRUCTIONS
  const canAdd = rows.length < MAX_INSTRUCTIONS

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className={FIELD_LABEL}>
          Instructions ({rows.length} / {MAX_INSTRUCTIONS})
        </span>
        <Button
          size="icon-xs"
          variant="outline"
          aria-label="Add instruction"
          onClick={addRow}
          disabled={!canAdd}
          className="rounded-full"
        >
          <Plus />
        </Button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={onDragEnd}
      >
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-1.5">
            {rows.map((row, idx) => (
              <SortableInstruction
                key={row.id}
                id={row.id}
                value={row.text}
                canDelete={canDelete}
                autoFocus={row.id === newRowIdRef.current}
                onChange={(text) => updateAt(idx, text)}
                onDelete={() => deleteAt(idx)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  )
}

function SortableInstruction({
  id,
  value,
  canDelete,
  autoFocus,
  onChange,
  onDelete,
}: {
  id: string
  value: string
  canDelete: boolean
  autoFocus: boolean
  onChange: (text: string) => void
  onDelete: () => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const [draft, setDraft] = useState(value)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    setDraft(value)
  }, [value])

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus()
  }, [autoFocus])

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-start gap-1.5 rounded-md border bg-background px-1.5 py-1.5",
        isDragging && "opacity-60 shadow-md",
      )}
    >
      <button
        type="button"
        aria-label="Drag to reorder"
        className="mt-1 flex size-6 shrink-0 cursor-grab items-center justify-center text-muted-foreground hover:text-foreground active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-3.5" />
      </button>
      <Textarea
        ref={inputRef}
        value={draft}
        rows={2}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          if (draft !== value) onChange(draft)
        }}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault()
            ;(e.target as HTMLTextAreaElement).blur()
          }
          if (e.key === "Escape") {
            setDraft(value)
            ;(e.target as HTMLTextAreaElement).blur()
          }
        }}
        placeholder="Instruction text"
        className="min-w-0 flex-1 resize-none border-none bg-transparent p-1 text-s shadow-none focus-visible:ring-1 focus-visible:ring-ring/50 md:text-s"
      />
      <Button
        type="button"
        size="icon-xs"
        variant="ghost"
        aria-label="Delete instruction"
        disabled={!canDelete}
        onClick={onDelete}
        className="text-muted-foreground hover:text-foreground"
      >
        <X />
      </Button>
    </div>
  )
}
