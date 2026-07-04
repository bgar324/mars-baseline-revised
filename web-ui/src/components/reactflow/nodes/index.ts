import { AgentNode } from "./agent"
import { ClaimNode } from "./claim"
import { DebateNode } from "./debate"
import { ResearchNode } from "./research"

export const nodeTypes = {
  research: ResearchNode,
  claim: ClaimNode,
  agent: AgentNode,
  debate: DebateNode,
} as const
