"use client"

import { useEffect, useRef, useState } from "react"
import {
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Link as LinkIcon,
  Users,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Paper } from "@/types/paper"

const FIELD_LABEL =
  "font-mono text-[10px] uppercase tracking-wide text-muted-foreground"

export function PaperCard({
  paper,
  expanded,
  onToggle,
}: {
  paper: Paper
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          onToggle()
        }
      }}
      className={cn(
        "w-full cursor-pointer rounded-md border bg-background p-3 text-left transition-colors hover:border-ring",
        expanded && "border-ring",
      )}
    >
      <h4 className="text-s font-medium leading-snug line-clamp-3">
        {paper.title}
      </h4>

      {paper.authors.length > 0 && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="size-3.5 shrink-0" />
          <span className="truncate">
            {paper.authors
              .slice(0, 2)
              .map((a) => a.name)
              .join(", ")}
            {paper.authors.length > 2 && (
              <span className="ml-1">+{paper.authors.length - 2} more</span>
            )}
          </span>
        </div>
      )}

      {paper.venue && (
        <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
          <BookOpen className="size-3.5 shrink-0" />
          <span className="truncate">{paper.venue}</span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-end gap-2 text-xs text-muted-foreground">
        <MetaLine year={paper.year} citations={paper.citation_count} />
        {expanded ? (
          <ChevronUp className="size-3.5" />
        ) : (
          <ChevronDown className="size-3.5" />
        )}
      </div>

      {expanded && (
        <div className="mt-3 space-y-3 border-t pt-3">
          {paper.tldr && (
            <div>
              <div className={cn(FIELD_LABEL, "mb-1")}>Overview</div>
              <p className="text-s leading-relaxed">{paper.tldr}</p>
            </div>
          )}
          {paper.abstract && (
            <div>
              <div className={cn(FIELD_LABEL, "mb-1")}>Abstract</div>
              <AbstractText text={paper.abstract} />
            </div>
          )}
          <ActionLinks paper={paper} />
        </div>
      )}
    </div>
  )
}

function AbstractText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const [isClamped, setIsClamped] = useState(false)
  const pRef = useRef<HTMLParagraphElement | null>(null)

  useEffect(() => {
    const el = pRef.current
    if (!el || expanded) return
    setIsClamped(el.scrollHeight > el.clientHeight + 1)
  }, [text, expanded])

  return (
    <div className="leading-relaxed">
      <p
        ref={pRef}
        className={cn("text-s leading-relaxed", !expanded && "line-clamp-4")}
      >
        {text}
      </p>
      {isClamped && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded((v) => !v)
          }}
          className="mt-1 text-s font-medium text-primary hover:underline"
        >
          {expanded ? "less" : "…more"}
        </button>
      )}
    </div>
  )
}

function MetaLine({
  year,
  citations,
}: {
  year: number | null | undefined
  citations: number | null | undefined
}) {
  const parts: string[] = []
  if (year != null) parts.push(String(year))
  if (citations != null) {
    parts.push(`${citations} ${citations === 1 ? "CITATION" : "CITATIONS"}`)
  }
  if (parts.length === 0) return null
  return <span>{parts.join(" · ")}</span>
}

function ActionLinks({ paper }: { paper: Paper }) {
  const links: { href: string; label: string; icon: React.ReactNode }[] = []
  if (paper.url) {
    links.push({
      href: paper.url,
      label: "Source",
      icon: <ArrowUpRight className="size-3.5" />,
    })
  }
  if (paper.doi) {
    links.push({
      href: `https://doi.org/${paper.doi}`,
      label: "DOI",
      icon: <LinkIcon className="size-3.5" />,
    })
  }
  if (links.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((l) => (
        <Button
          key={l.label}
          asChild
          size="xs"
          variant="outline"
          className="rounded-full"
          onClick={(e) => e.stopPropagation()}
        >
          <a href={l.href} target="_blank" rel="noopener noreferrer">
            {l.icon}
            {l.label}
          </a>
        </Button>
      ))}
    </div>
  )
}
