"use client"

import { ArrowUpRight, BookOpen, Users } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import type { Paper } from "@/types/paper"

export function InlineCitation({
  paper,
  index,
  className,
}: {
  paper: Paper
  index: number
  className?: string
}) {
  const href = paper.url ?? (paper.doi ? `https://doi.org/${paper.doi}` : null)
  return (
    <HoverCard openDelay={100} closeDelay={120}>
      <HoverCardTrigger asChild>
        <a
          href={href ?? "#"}
          target={href ? "_blank" : undefined}
          rel={href ? "noopener noreferrer" : undefined}
          onClick={(e) => {
            if (!href) e.preventDefault()
          }}
          className="inline-flex align-baseline"
        >
          <Badge
            variant="secondary"
            className={cn(
              "ml-0.5 h-4 cursor-pointer rounded-full px-1.5 py-0 text-[10px] font-medium leading-none tabular-nums",
              "hover:bg-primary/15",
              className,
            )}
          >
            {index}
          </Badge>
        </a>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 space-y-1.5">
        <h4 className="line-clamp-3 text-s font-medium leading-snug">
          {paper.title}
        </h4>
        {paper.authors.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Users className="size-3 shrink-0" />
            <span className="truncate">
              {paper.authors
                .slice(0, 3)
                .map((a) => a.name)
                .join(", ")}
              {paper.authors.length > 3 && (
                <span className="ml-1">+{paper.authors.length - 3} more</span>
              )}
            </span>
          </div>
        )}
        {paper.venue && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <BookOpen className="size-3 shrink-0" />
            <span className="truncate">{paper.venue}</span>
          </div>
        )}
        <div className="flex items-center justify-between gap-2 pt-1 text-xs text-muted-foreground">
          <span>
            {paper.year ?? ""}
            {paper.citation_count != null
              ? ` · ${paper.citation_count} cites`
              : ""}
          </span>
          {href && <ArrowUpRight className="size-3" />}
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}
