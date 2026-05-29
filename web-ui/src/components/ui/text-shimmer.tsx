"use client"

import { cn } from "@/lib/utils"

export type TextShimmerProps = {
  as?: string
  duration?: number
  spread?: number
  children: React.ReactNode
} & React.HTMLAttributes<HTMLElement>

const SHIMMER_BASE = "color-mix(in oklab, var(--muted-foreground) 50%, transparent)"

export function TextShimmer({
  as = "span",
  className,
  duration = 2.4,
  spread = 20,
  children,
  ...props
}: TextShimmerProps) {
  const dynamicSpread = Math.min(Math.max(spread, 5), 45)
  const Component = as as React.ElementType

  return (
    <Component
      className={cn(
        "bg-size-[200%_auto] bg-clip-text font-medium text-transparent",
        "animate-[shimmer_2.4s_infinite_linear]",
        className,
      )}
      style={{
        backgroundImage: `linear-gradient(to right, ${SHIMMER_BASE} ${50 - dynamicSpread}%, var(--foreground) 50%, ${SHIMMER_BASE} ${50 + dynamicSpread}%)`,
        animationDuration: `${duration}s`,
      }}
      {...props}
    >
      {children}
    </Component>
  )
}
