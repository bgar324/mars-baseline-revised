import {
  BaseEdge,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react"

import type { CanvasEdgeVariant } from "@/features/hypo-canvas/types"

export type ChainEdgeData = { variant?: CanvasEdgeVariant }
type ChainEdge = Edge<ChainEdgeData, "chain">

const STYLE: Record<CanvasEdgeVariant, React.CSSProperties> = {
  solid: {
    stroke: "#339ccc",
    strokeWidth: 1.2,
  },
  dashed: {
    stroke: "#339ccc",
    strokeWidth: 1.5,
    strokeDasharray: "6 4",
  },
  animated: {
    stroke: "#339ccc",
    strokeWidth: 1.5,
    strokeDasharray: "6 4",
  },
  faded: {
    stroke: "#e2e8f0",
    strokeWidth: 1,
  },
}

export function ChainEdge(props: EdgeProps<ChainEdge>) {
  const [path] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition,
  })
  const variant: CanvasEdgeVariant = props.data?.variant ?? "solid"
  const className =
    variant === "animated"
      ? "[animation:dashdraw_1s_linear_infinite]"
      : undefined
  return (
    <BaseEdge
      id={props.id}
      path={path}
      style={STYLE[variant]}
      className={className}
    />
  )
}
