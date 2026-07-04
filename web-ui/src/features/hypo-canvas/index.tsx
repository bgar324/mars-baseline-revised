"use client"

import { useEffect, useMemo } from "react"
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
import { useDebate } from "@/hooks/use-debate"
import { useExtraction } from "@/hooks/use-extraction"
import { useHypotheses } from "@/hooks/use-hypotheses"
import { usePersonas } from "@/hooks/use-personas"
import { useQueryEvents } from "@/hooks/use-query-events"
import { useAgentBuilderStore } from "@/store/agent-builder"

import { deriveEdges, deriveNodes, layoutNodes } from "./derive"
import {
  canvasShiftViewportRef,
  leftPanelRef,
  rightPanelRef,
} from "./panel-refs"
import { useSelectionStore } from "./selection-store"
import { useBuilderSnapshot } from "./use-builder-snapshot"

type AdjustableNodeType = "research" | "claim" | "agent" | "debate"

function typeForCanvasNodeId(id: string): AdjustableNodeType | null {
  if (id === "research") return "research"
  if (id === "claim") return "claim"
  if (/^agent-\d+$/.test(id)) return "agent"
  if (id === "debate") return "debate"
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
    case "debate":
      leftPanelRef.current?.collapse()
      rightPanelRef.current?.expand()
      return
  }
}

export function HypoCanvas() {
  const queryId = useAgentBuilderStore((s) => s.queryId)
  const builder = useBuilderSnapshot()
  const nodeSelected = useSelectionStore((s) => s.nodeSelected)
  const nodeTypes = useMemo(() => NODE_TYPES, [])
  const edgeTypes = useMemo(() => EDGE_TYPES, [])

  useQueryEvents(queryId)
  useExtraction()
  usePersonas()
  useDebate()
  useHypotheses()

  const selectedNodeId = useSelectionStore((s) => s.selectedNodeId)
  useEffect(() => {
    if (!selectedNodeId) return
    const type = typeForCanvasNodeId(selectedNodeId)
    if (type) adjustPanelsFor(type)
  }, [selectedNodeId])

  const { nodes, edges } = useMemo(() => {
    const baseNodes = deriveNodes(builder)
    const baseEdges = deriveEdges(builder)
    const laid = layoutNodes(baseNodes, baseEdges)
    return { nodes: laid as RFNode[], edges: baseEdges as RFEdge[] }
  }, [builder])

  const onNodeClick: NodeMouseHandler = (_, node) => {
    const t = typeForCanvasNodeId(node.id)
    if (!t) return
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
    if (prevType === "agent" || prevType === "debate") {
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
