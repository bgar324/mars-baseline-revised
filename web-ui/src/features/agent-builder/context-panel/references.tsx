"use client"

import { useMemo, useState } from "react"

import { PaperCard } from "@/components/common/paper-card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { usePapers } from "@/hooks/use-papers"
import type { Paper } from "@/types/paper"
import type { PersonaAgent } from "@/types/persona"

type SortKey = "year" | "citation_count" | "influential_citation_count"

const SORT_LABEL: Record<SortKey, string> = {
  year: "Year",
  citation_count: "Citations",
  influential_citation_count: "Influential cites",
}

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

export function References({ persona }: { persona: PersonaAgent }) {
  const { data, isFetching, isError } = usePapers()
  const [sort, setSort] = useState<SortKey>("year")
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const papers = useMemo(() => {
    if (!data) return [] as Paper[]
    const refs = new Set(persona.references)
    const filtered = data.filter((p) => refs.has(p.id))
    const cmp = (a: Paper, b: Paper) => (b[sort] ?? 0) - (a[sort] ?? 0)
    return [...filtered].sort(cmp)
  }, [data, persona.references, sort])

  if (isError) {
    return (
      <p className="text-s text-muted-foreground">
        Couldn&apos;t load references for this session.
      </p>
    )
  }

  if (isFetching && !data) {
    return (
      <div className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-24 w-full animate-pulse rounded-md bg-muted"
          />
        ))}
      </div>
    )
  }

  if (papers.length === 0) {
    return (
      <p className="text-s text-muted-foreground">
        No references for this researcher.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className={SECTION_LABEL}>
          {papers.length === 1 ? "Paper" : "Papers"} ({papers.length})
        </span>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="h-7 w-auto gap-1 border-none bg-transparent px-2 text-xs shadow-none [&_span.font-medium]:text-xs!">
            <span className="text-muted-foreground">Sort:</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent position="popper" align="end">
            {(Object.keys(SORT_LABEL) as SortKey[]).map((k) => (
              <SelectItem key={k} value={k}>
                <span className="text-s font-medium">{SORT_LABEL[k]}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        {papers.map((paper) => (
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
    </div>
  )
}

