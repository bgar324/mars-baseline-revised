import { Handle, Position } from "@xyflow/react"

import { cn } from "@/lib/utils"

export function ChainHandle({
  position,
  id,
  className,
}: {
  position: "top" | "bottom"
  id?: string
  className?: string
}) {
  return (
    <Handle
      type={position === "top" ? "target" : "source"}
      position={position === "top" ? Position.Top : Position.Bottom}
      id={id}
      isConnectable={false}
      className={cn(
        "pointer-events-none !size-1 !min-h-0 !min-w-0 !rounded-full !border-0 !bg-transparent !opacity-0",
        className,
      )}
    />
  )
}
