"use client"

import { RotateCcw } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { BuilderPanel } from "@/features/agent-builder/builder-panel"
import { ContextPanel } from "@/features/agent-builder/context-panel"
import { useSessionReset } from "@/features/agent-builder/use-session-reset"
import { HypoCanvas } from "@/features/hypo-canvas"
import { DebatePanel } from "@/features/hypo-canvas/debate-panel"
import {
  canvasShiftViewportRef,
  leftPanelRef,
  rightPanelRef,
} from "@/features/hypo-canvas/panel-refs"
import { useSelectionStore } from "@/features/hypo-canvas/selection-store"
import { SteerPanel } from "@/features/hypo-canvas/steer-panel"

const SIDE_DEFAULT = "25%"
const SIDE_MIN = "20%"
const CENTER_DEFAULT = "50%"
const CENTER_MIN = "30%"

const HANDLE_CLASS =
  "before:bg-muted-foreground/20 hover:before:bg-muted-foreground/40 active:before:bg-primary before:pointer-events-none before:absolute before:top-1/2 before:left-1/2 before:z-10 before:h-8 before:w-1 before:-translate-x-1/2 before:-translate-y-1/2 before:scale-y-75 before:rounded-full before:transition-all before:duration-300 before:ease-[cubic-bezier(0.32,0.72,0,1)] hover:before:scale-y-100 active:before:h-14 active:before:w-1.5 active:before:scale-y-100"

export default function CanvasPage() {
  const selectedNodeId = useSelectionStore((s) => s.selectedNodeId)
  const resetSession = useSessionReset()
  const leftLabel = "▦ AGENT BUILDER"
  const rightLabel =
    selectedNodeId && /^[sd]\d+$/.test(selectedNodeId)
      ? "▦ AGENT WORKFLOW"
      : "▦ AGENT BUILDER"

  return (
    <div className="flex h-screen w-screen flex-col">
      <header className="flex h-12 shrink-0 items-center justify-between border-b px-4">
        <div className="w-24" />
        <h1 className="font-sans text-sm uppercase tracking-wide">
          Hypothesis Canvas
        </h1>
        <div className="flex w-24 justify-end">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="xs">
                <RotateCcw />
                Reset
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent
              className="h-fit!"
              style={{
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                margin: "auto",
                transform: "none",
              }}
            >
              <AlertDialogHeader>
                <AlertDialogTitle className="tracking-normal">
                  Discard this session?
                </AlertDialogTitle>
                <AlertDialogDescription>
                  Your team and selected researchers will be cleared so you
                  can start a new research query.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep current</AlertDialogCancel>
                <AlertDialogAction
                  variant="destructive"
                  onClick={resetSession}
                >
                  Discard
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </header>
      <ResizablePanelGroup
        orientation="horizontal"
        className="min-h-0 flex-1 overflow-hidden"
      >
        <ResizablePanel
          panelRef={leftPanelRef}
          defaultSize={SIDE_DEFAULT}
          minSize={SIDE_MIN}
          collapsible
          collapsedSize={0}
          onResize={(size, _id, prev) => {
            if (!prev) return
            const delta = size.inPixels - prev.inPixels
            if (delta !== 0) canvasShiftViewportRef.current?.(-delta)
          }}
          className="min-w-0"
        >
          <PanelChrome label={leftLabel}>
            <BuilderPanel />
          </PanelChrome>
        </ResizablePanel>
        <ResizableHandle className={HANDLE_CLASS} />
        <ResizablePanel
          defaultSize={CENTER_DEFAULT}
          minSize={CENTER_MIN}
          className="min-w-0"
        >
          <HypoCanvas />
        </ResizablePanel>
        <ResizableHandle className={HANDLE_CLASS} />
        <ResizablePanel
          panelRef={rightPanelRef}
          defaultSize={SIDE_DEFAULT}
          minSize={SIDE_MIN}
          collapsible
          collapsedSize={0}
          className="min-w-0"
        >
          <PanelChrome label={rightLabel}>
            <RightPaneContent />
          </PanelChrome>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

function PanelChrome({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-9 shrink-0 items-center border-b px-3">
        <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  )
}

function RightPaneContent() {
  const id = useSelectionStore((s) => s.selectedNodeId)
  if (id && /^s\d+$/.test(id)) return <SteerPanel canvasCycleId={id} />
  if (id && /^d\d+$/.test(id)) return <DebatePanel canvasCycleId={id} />
  return <ContextPanel />
}
