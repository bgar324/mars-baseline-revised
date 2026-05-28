import { Separator } from "@/components/ui/separator"

import { QueryInput } from "./query-input"
import { ResearcherPool } from "./agent-card"
import { TeamSelector } from "./team-selector"

export function BuilderPanel() {
  return (
    <div className="flex h-full min-w-0 flex-col gap-1 overflow-x-hidden overflow-y-auto p-3">
      <QueryInput />
      <Separator className="my-3" />
      <TeamSelector />
      <Separator className="my-3" />
      <ResearcherPool />
    </div>
  )
}
