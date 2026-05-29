"use client"

import { Streamdown } from "streamdown"

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

export function StreamingMarkdown({
  text,
  isStreaming = false,
  className,
}: {
  text: string
  isStreaming?: boolean
  className?: string
}) {
  const revealed = useTypewriter(text, isStreaming)
  return (
    <Streamdown
      className={cn(className, isStreaming && CARET_CSS)}
      isAnimating={isStreaming}
      caret={isStreaming ? "circle" : undefined}
      mode={isStreaming ? "streaming" : "static"}
      parseIncompleteMarkdown
    >
      {revealed}
    </Streamdown>
  )
}
