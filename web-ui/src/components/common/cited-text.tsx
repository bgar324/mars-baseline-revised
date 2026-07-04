"use client"

import { Fragment } from "react"

import { InlineCitation } from "@/components/common/inline-citation"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Paper } from "@/types/paper"

const TOKEN = /\[\s*\d{6,}(?:\s*,\s*\d{6,})*\s*\]|\d{6,}/g
const DIGITS = /\d{6,}/g

export function buildCitationNumbering(texts: string[]): Map<string, number> {
  const map = new Map<string, number>()
  let n = 0
  for (const text of texts) {
    for (const m of text.matchAll(DIGITS)) {
      if (!map.has(m[0])) map.set(m[0], ++n)
    }
  }
  return map
}

function MutedMarker({ index }: { index: number }) {
  return (
    <Badge
      variant="secondary"
      className="ml-0.5 h-4 rounded-full px-1.5 py-0 text-[10px] font-medium leading-none tabular-nums opacity-50"
    >
      {index}
    </Badge>
  )
}

export function CitedText({
  text,
  papersByCorpusId,
  numberOf,
  className,
}: {
  text: string
  papersByCorpusId: Map<string, Paper>
  numberOf: (corpusId: string) => number
  className?: string
}) {
  const nodes: React.ReactNode[] = []
  let last = 0
  let k = 0
  for (const m of text.matchAll(TOKEN)) {
    const start = m.index ?? 0
    if (start > last) {
      nodes.push(<Fragment key={k++}>{text.slice(last, start)}</Fragment>)
    }
    for (const id of m[0].match(DIGITS) ?? []) {
      const paper = papersByCorpusId.get(id)
      nodes.push(
        paper ? (
          <InlineCitation key={k++} paper={paper} index={numberOf(id)} />
        ) : (
          <MutedMarker key={k++} index={numberOf(id)} />
        ),
      )
    }
    last = start + m[0].length
  }
  if (last < text.length) {
    nodes.push(<Fragment key={k++}>{text.slice(last)}</Fragment>)
  }
  return <span className={cn(className)}>{nodes}</span>
}
