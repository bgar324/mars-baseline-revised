import { createRef, type RefObject } from "react"
import type { PanelImperativeHandle } from "react-resizable-panels"

export const leftPanelRef: RefObject<PanelImperativeHandle | null> = createRef()
export const rightPanelRef: RefObject<PanelImperativeHandle | null> = createRef()

export const canvasShiftViewportRef: RefObject<((dx: number) => void) | null> =
  createRef()
