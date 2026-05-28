"use client"

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { BuilderPanel } from "@/features/agent-builder/builder-panel"
import { ContextPanel } from "@/features/agent-builder/context-panel"
import { ResearchStudio } from "@/features/research-studio"

const SIDE_DEFAULT = "25%"
const SIDE_MIN = "20%"
const CENTER_DEFAULT = "50%"
const CENTER_MIN = "30%"

const HANDLE_CLASS =
  "before:bg-muted-foreground/20 hover:before:bg-muted-foreground/40 active:before:bg-primary before:pointer-events-none before:absolute before:top-1/2 before:left-1/2 before:z-10 before:h-8 before:w-1 before:-translate-x-1/2 before:-translate-y-1/2 before:scale-y-75 before:rounded-full before:transition-all before:duration-300 before:ease-[cubic-bezier(0.32,0.72,0,1)] hover:before:scale-y-100 active:before:h-14 active:before:w-1.5 active:before:scale-y-100"

export function AgentBuilderWorkspace() {
  return (
    <ResizablePanelGroup
      orientation="horizontal"
      className="h-full w-full overflow-hidden"
    >
      <ResizablePanel
        defaultSize={SIDE_DEFAULT}
        minSize={SIDE_MIN}
        className="min-w-0"
      >
        <BuilderPanel />
      </ResizablePanel>
      <ResizableHandle className={HANDLE_CLASS} />
      <ResizablePanel
        defaultSize={CENTER_DEFAULT}
        minSize={CENTER_MIN}
        className="min-w-0"
      >
        <ResearchStudio />
      </ResizablePanel>
      <ResizableHandle className={HANDLE_CLASS} />
      <ResizablePanel
        defaultSize={SIDE_DEFAULT}
        minSize={SIDE_MIN}
        className="min-w-0"
      >
        <ContextPanel />
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
