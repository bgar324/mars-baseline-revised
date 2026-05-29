"use client"

import { TextShimmer } from "@/components/ui/text-shimmer"
import { cn } from "@/lib/utils"

export type ThinkingBarProps = {
  text?: string
  className?: string
}

export function ThinkingBar({ text = "Thinking…", className }: ThinkingBarProps) {
  return (
    <div className={cn("flex w-full items-center", className)}>
      <TextShimmer className="text-s font-medium">{text}</TextShimmer>
    </div>
  )
}
