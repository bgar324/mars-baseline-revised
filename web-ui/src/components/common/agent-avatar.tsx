"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"
import { useAgentColor } from "@/utils/agent-color"
import { initials } from "@/utils/avatar"

export function AgentAvatar({
  clusterId,
  name,
  className,
  fallbackClassName,
}: {
  clusterId: number
  name: string
  className?: string
  fallbackClassName?: string
}) {
  const color = useAgentColor(clusterId)
  return (
    <Avatar className={className}>
      <AvatarFallback className={cn(color.solid, fallbackClassName)}>
        {initials(name)}
      </AvatarFallback>
    </Avatar>
  )
}
