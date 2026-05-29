import { AgentNode } from "./agent"
import { ClaimNode } from "./claim"
import { DebateNode } from "./debate"
import { PlaceholderNode } from "./placeholder"
import { ResearchNode } from "./research"
import { SteerNode } from "./steer"

export const nodeTypes = {
  research: ResearchNode,
  claim: ClaimNode,
  agent: AgentNode,
  steer: SteerNode,
  debate: DebateNode,
  placeholder: PlaceholderNode,
} as const
