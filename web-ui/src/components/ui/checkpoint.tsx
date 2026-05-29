"use client"

import type { ComponentProps } from "react"
import type { LucideIcon } from "lucide-react"

import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

const LABEL = "font-mono text-xs uppercase tracking-wide text-muted-foreground"

export type CheckpointProps = ComponentProps<"div"> & {
  icon?: LucideIcon
  label: string
}

export function Checkpoint({
  icon: Icon,
  label,
  className,
  ...props
}: CheckpointProps) {
  return (
    <div
      className={cn("flex items-center gap-2 text-muted-foreground", className)}
      {...props}
    >
      {Icon ? <Icon className="size-3.5 shrink-0" /> : null}
      <span className={cn(LABEL, "shrink-0")}>{label}</span>
      <Separator className="flex-1" />
    </div>
  )
}
