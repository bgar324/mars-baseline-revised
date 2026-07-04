import { Separator } from "@/components/ui/separator"

import { QueryInput } from "./query-input"
import { ResearcherPool } from "./agent-card"
import { SessionSummary } from "./session-summary"

export function BuilderPanel() {
  return (
    <div className="flex h-full min-w-0 flex-col gap-1 overflow-x-hidden overflow-y-auto p-3">
      <QueryInput />
      <SessionSummary />
      <Separator className="my-3" />
      <ResearcherPool />
    </div>
  )
}
