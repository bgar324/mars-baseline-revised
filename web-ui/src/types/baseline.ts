import { z } from "zod"

export const BaselineMessageSchema = z.object({
  message_id: z.string(),
  role: z.enum(["user", "agent"]),
  content: z.string(),
  agent_id: z.string().nullable().optional(),
  rationale: z.string().nullable().optional(),
  evidence: z.array(z.string()).default([]),
  created_at: z.string(),
})

export const BaselineConversationSchema = z.object({
  messages: z.array(BaselineMessageSchema).default([]),
})

export type BaselineMessage = z.infer<typeof BaselineMessageSchema>
export type BaselineConversation = z.infer<typeof BaselineConversationSchema>
