import * as React from "react"

import { cn } from "@/lib/utils"

const SECTION_LABEL =
  "font-mono text-xs uppercase tracking-wide text-muted-foreground"

function BasePanel({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="base-panel"
      className={cn(
        "flex h-full min-w-0 flex-col overflow-hidden rounded-md border bg-background",
        className,
      )}
      {...props}
    />
  )
}

function BasePanelHeader({
  className,
  ...props
}: React.ComponentProps<"header">) {
  return (
    <header
      data-slot="base-panel-header"
      className={cn(
        "flex shrink-0 items-center justify-between gap-2 border-b px-4 py-3",
        className,
      )}
      {...props}
    />
  )
}

function BasePanelTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="base-panel-title"
      className={cn("text-s font-medium", className)}
      {...props}
    />
  )
}

function BasePanelBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="base-panel-body"
      className={cn("flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4", className)}
      {...props}
    />
  )
}

function BasePanelSection({
  title,
  className,
  children,
  ...props
}: React.ComponentProps<"section"> & { title?: React.ReactNode }) {
  return (
    <section
      data-slot="base-panel-section"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    >
      {title != null && <span className={SECTION_LABEL}>{title}</span>}
      {children}
    </section>
  )
}

function BasePanelFooter({
  className,
  ...props
}: React.ComponentProps<"footer">) {
  return (
    <footer
      data-slot="base-panel-footer"
      className={cn(
        "flex shrink-0 items-center justify-between gap-2 border-t px-4 py-3",
        className,
      )}
      {...props}
    />
  )
}

export {
  BasePanel,
  BasePanelHeader,
  BasePanelTitle,
  BasePanelBody,
  BasePanelSection,
  BasePanelFooter,
}
