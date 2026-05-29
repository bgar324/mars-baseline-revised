"use client"

import { useMemo } from "react"
import { Streamdown } from "streamdown"
import type { Components } from "streamdown"

import { useTypewriter } from "@/hooks/use-typewriter"
import { cn } from "@/lib/utils"

const CARET_CSS = [
  "[&_[data-streamdown=caret]]:ml-0.5",
  "[&_[data-streamdown=caret]]:inline-block",
  "[&_[data-streamdown=caret]]:size-1.5",
  "[&_[data-streamdown=caret]]:rounded-full",
  "[&_[data-streamdown=caret]]:bg-foreground",
  "[&_[data-streamdown=caret]]:animate-pulse",
].join(" ")

const ALLOWED_TAGS = { mention: [] }
const LITERAL_TAG_CONTENT = ["mention"]

function Mention({ children }: { children?: React.ReactNode }) {
  return (
    <span className="whitespace-nowrap rounded bg-primary/10 px-1 font-medium text-primary">
      {children}
    </span>
  )
}

const COMPONENTS = { mention: Mention } as unknown as Components

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function linkifyMentions(text: string, names: string[]): string {
  const usable = names.filter((n) => n.trim().length > 0)
  if (usable.length === 0) return text
  const pattern = [...usable]
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp)
    .join("|")
  const re = new RegExp(`(?<!\\w)@?(${pattern})`, "g")
  return text.replace(re, (_full, name) => `<mention>@${name}</mention>`)
}

export function StreamingMarkdown({
  text,
  isStreaming = false,
  className,
  mentions,
}: {
  text: string
  isStreaming?: boolean
  className?: string
  mentions?: string[]
}) {
  const revealed = useTypewriter(text, isStreaming)
  const content = useMemo(
    () => linkifyMentions(revealed, mentions ?? []),
    [revealed, mentions],
  )
  return (
    <Streamdown
      className={cn(className, isStreaming && CARET_CSS)}
      isAnimating={isStreaming}
      caret={isStreaming ? "circle" : undefined}
      mode={isStreaming ? "streaming" : "static"}
      components={COMPONENTS}
      allowedTags={ALLOWED_TAGS}
      literalTagContent={LITERAL_TAG_CONTENT}
      parseIncompleteMarkdown
    >
      {content}
    </Streamdown>
  )
}
