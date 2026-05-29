"use client"

import { useEffect, useMemo, useRef } from "react"
import {
  Background,
  BackgroundVariant,
  ReactFlow,
  useNodes,
  useReactFlow,
  type Edge as RFEdge,
  type Node as RFNode,
  type NodeMouseHandler,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import "@/styles/canvas.css"

import { edgeTypes as EDGE_TYPES } from "@/components/reactflow/edges"
import { nodeTypes as NODE_TYPES } from "@/components/reactflow/nodes"
import { useCreateDebate } from "@/hooks/use-create-debate"
import { useDebateEvents } from "@/hooks/use-debate-events"
import { useProposeTurn } from "@/hooks/use-propose-turn"
import { useRunCycle } from "@/hooks/use-run-cycle"
import { useAgentBuilderStore } from "@/store/agent-builder"

import { useChainStore } from "./chain-store"
import { useDebateStore } from "./debate-store"
import { deriveEdges, deriveNodes, layoutNodes } from "./derive"
import {
  canvasShiftViewportRef,
  leftPanelRef,
  rightPanelRef,
} from "./panel-refs"
import { useSelectionStore } from "./selection-store"
import { useBuilderSnapshot } from "./use-builder-snapshot"

type AdjustableNodeType =
  | "research"
  | "claim"
  | "agent"
  | "steer"
  | "debate"

function typeForCanvasNodeId(id: string): AdjustableNodeType | null {
  if (id === "research") return "research"
  if (id === "claim") return "claim"
  if (/^agent-[1-3]$/.test(id)) return "agent"
  if (/^s\d+$/.test(id)) return "steer"
  if (/^d\d+$/.test(id)) return "debate"
  return null
}

function adjustPanelsFor(type: AdjustableNodeType) {
  switch (type) {
    case "research":
    case "claim":
      leftPanelRef.current?.expand()
      rightPanelRef.current?.collapse()
      return
    case "agent":
      leftPanelRef.current?.expand()
      rightPanelRef.current?.expand()
      return
    case "steer":
    case "debate":
      leftPanelRef.current?.collapse()
      rightPanelRef.current?.expand()
      return
  }
}

export function HypoCanvas() {
  const builder = useBuilderSnapshot()
  const cycles = useChainStore((s) => s.cycles)
  const nextPlaceholder = useChainStore((s) => s.nextPlaceholder)
  const blockedReason = useChainStore((s) => s.blockedReason)
  const nodeSelected = useSelectionStore((s) => s.nodeSelected)
  const debateId = useDebateStore((s) => s.debateId)
  const createDebate = useCreateDebate()
  const runCycle = useRunCycle()
  const proposeTurn = useProposeTurn()
  const activatingRef = useRef(false)
  const nodeTypes = useMemo(() => NODE_TYPES, [])
  const edgeTypes = useMemo(() => EDGE_TYPES, [])
  useDebateEvents(debateId)

  useEffect(() => {
    if (cycles.length > 0) return
    const setPlaceholder = useChainStore.getState().placeholderSet
    if (builder.team.length === 3 && builder.focalClaim != null) {
      setPlaceholder({ kind: "steer", n: 0 })
    } else {
      setPlaceholder(null)
    }
  }, [builder.team.length, builder.focalClaim, cycles.length])

  const selectedNodeId = useSelectionStore((s) => s.selectedNodeId)
  useEffect(() => {
    if (!selectedNodeId) return
    const type = typeForCanvasNodeId(selectedNodeId)
    if (type) adjustPanelsFor(type)
  }, [selectedNodeId])

  const onActivatePlaceholder = async () => {
    if (activatingRef.current) return
    activatingRef.current = true
    try {
      const chain = useChainStore.getState()
      const debate = useDebateStore.getState()
      const nxt = chain.nextPlaceholder
      if (!nxt) return

      if (nxt.kind === "steer" && nxt.n === 0) {
        const { rootId } = await createDebate.mutateAsync()
        chain.steerAdvanced(0)
        useDebateStore.getState().cycleMapped("s0", rootId)
        chain.placeholderSet({ kind: "debate", n: 1 })
        useSelectionStore.getState().nodeSelected("s0")

        const team = useAgentBuilderStore.getState().team
        const debateId = useDebateStore.getState().debateId
        if (debateId) {
          await Promise.allSettled(
            team.slice(0, 3).map((p) =>
              proposeTurn.mutateAsync({
                debateId,
                backendCycleId: rootId,
                canvasCycleId: "s0",
                agentId: String(p.cluster_id),
                steers: [],
              }),
            ),
          )
        }
      } else if (nxt.kind === "debate") {
        const canvasSteerId = `s${nxt.n - 1}`
        const backendCycleId = debate.canvasToBackend[canvasSteerId]
        const debateId = debate.debateId
        if (!debateId || !backendCycleId) {
          console.error("[activate] missing debate or cycle id")
          return
        }
        chain.placeholderSet(null)
        chain.debateAdvanced(nxt.n)
        useDebateStore.getState().cycleMapped(`d${nxt.n}`, backendCycleId)
        chain.cycleStatusChanged(`d${nxt.n}`, "running")
        useSelectionStore.getState().nodeSelected(`d${nxt.n}`)
        adjustPanelsFor("debate")
        try {
          await runCycle.mutateAsync({ debateId, cycleId: backendCycleId })
          chain.cycleStatusChanged(`d${nxt.n}`, "done")
        } catch (err) {
          chain.cycleStatusChanged(`d${nxt.n}`, "faded")
          console.error("[activate] run-cycle failed", err)
        }
      } else if (nxt.kind === "steer") {
        chain.steerAdvanced(nxt.n)
        chain.placeholderSet(null)
        useSelectionStore.getState().nodeSelected(`s${nxt.n}`)
        adjustPanelsFor("steer")
      }
    } finally {
      activatingRef.current = false
    }
  }

  const { nodes, edges } = useMemo(() => {
    const baseNodes = deriveNodes(
      { cycles, nextPlaceholder, blockedReason },
      builder,
    )
    const baseEdges = deriveEdges({ cycles, nextPlaceholder }, builder)
    const laid = layoutNodes(baseNodes, baseEdges)
    const withHandlers = laid.map((n) =>
      n.type === "placeholder"
        ? { ...n, data: { ...n.data, onActivate: onActivatePlaceholder } }
        : n,
    ) as RFNode[]
    return { nodes: withHandlers, edges: baseEdges as RFEdge[] }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [builder, cycles, nextPlaceholder, blockedReason])

  const onNodeClick: NodeMouseHandler = (_, node) => {
    if (node.type === "placeholder") return
    const t = node.type as AdjustableNodeType
    if (t === "agent") {
      const persona = (node.data as { persona?: { cluster_id: number } })
        .persona
      if (persona) {
        useAgentBuilderStore.getState().agentSelected(persona.cluster_id)
      }
    }
    adjustPanelsFor(t)
    nodeSelected(node.id)
  }

  const onPaneClick = () => {
    const prev = useSelectionStore.getState().selectedNodeId
    const prevType = prev ? typeForCanvasNodeId(prev) : null
    nodeSelected(null)
    if (prevType === "agent" || prevType === "steer" || prevType === "debate") {
      rightPanelRef.current?.collapse()
    }
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      nodesDraggable
      nodesConnectable={false}
      elementsSelectable
      minZoom={0.1}
      maxZoom={4}
      fitView
      fitViewOptions={{ padding: 1.2, maxZoom: 0.9 }}
      deleteKeyCode={null}
      proOptions={{ hideAttribution: true }}
      className="h-full w-full"
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1.5} />
      <FocusController />
    </ReactFlow>
  )
}

function FocusController() {
  const { fitView, getViewport, setViewport } = useReactFlow()
  const nodes = useNodes()
  const idKey = nodes.map((n) => n.id).join(",")
  useEffect(() => {
    if (nodes.length === 0) return
    const raf = requestAnimationFrame(() => {
      fitView({
        nodes: nodes.map((n) => ({ id: n.id })),
        padding: 0.12,
        maxZoom: 1.5,
        duration: 400,
      })
    })
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idKey])

  useEffect(() => {
    canvasShiftViewportRef.current = (dx) => {
      if (dx === 0) return
      const v = getViewport()
      setViewport({ x: v.x + dx, y: v.y, zoom: v.zoom })
    }
    return () => {
      canvasShiftViewportRef.current = null
    }
  }, [getViewport, setViewport])

  return null
}
