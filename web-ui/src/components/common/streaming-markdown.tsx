"use client"

import { useMemo } from "react"
import { Streamdown } from "streamdown"
import type { Components } from "streamdown"

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
const DEFAULT_MENTION = "bg-muted text-muted-foreground"

export type Mention = {
  name: string
  className: string
}

function nodeText(node: React.ReactNode): string {
  if (typeof node === "string") return node
  if (Array.isArray(node)) return node.map(nodeText).join("")
  return ""
}

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
  mentions?: Mention[]
}) {
  const colors = useMemo(
    () => new Map((mentions ?? []).map((m) => [m.name, m.className])),
    [mentions],
  )
  const content = useMemo(
    () => linkifyMentions(text, [...colors.keys()]),
    [text, colors],
  )
  const components = useMemo(
    () =>
      ({
        mention: ({ children }: { children?: React.ReactNode }) => {
          const name = nodeText(children).replace(/^@/, "")
          return (
            <span
              className={cn(
                "whitespace-nowrap rounded px-1 font-medium",
                colors.get(name) ?? DEFAULT_MENTION,
              )}
            >
              {children}
            </span>
          )
        },
      }) as unknown as Components,
    [colors],
  )
  return (
    <Streamdown
      className={cn(className, isStreaming && CARET_CSS)}
      isAnimating={isStreaming}
      caret={isStreaming ? "circle" : undefined}
      mode={isStreaming ? "streaming" : "static"}
      components={components}
      allowedTags={ALLOWED_TAGS}
      literalTagContent={LITERAL_TAG_CONTENT}
      parseIncompleteMarkdown
    >
      {content}
    </Streamdown>
  )
}
