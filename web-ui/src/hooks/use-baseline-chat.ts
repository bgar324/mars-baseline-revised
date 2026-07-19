"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { useBaselineStore } from "@/store/baseline"
import {
  BaselineConversationSchema,
  type BaselineConversation,
} from "@/types/baseline"

async function fetchConversation(
  queryId: string,
  agentId: number,
): Promise<BaselineConversation> {
  return fetcher(
    `/api/query/${queryId}/baseline-chat?agent_id=${agentId}`,
    BaselineConversationSchema,
  )
}

export function useBaselineChat() {
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const debateStage = useAgentBuilderStore(
    (state) => state.pipelineStages.debate,
  )
  const agentId = useBaselineStore((state) => state.target)
  return useQuery({
    queryKey: ["baseline-chat", queryId, agentId],
    queryFn: () => fetchConversation(queryId!, agentId!),
    enabled: !!queryId && agentId != null && debateStage === "complete",
    staleTime: Infinity,
    gcTime: Infinity,
  })
}

export function useSendBaselineMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      message,
      agentId,
    }: {
      message: string
      agentId: number
    }) => {
      const queryId = useAgentBuilderStore.getState().queryId
      if (!queryId) throw new Error("no active query")
      return fetcher(
        `/api/query/${queryId}/baseline-chat`,
        BaselineConversationSchema,
        {
          method: "POST",
          body: JSON.stringify({
            message,
            agent_ids: [String(agentId)],
          }),
        },
      )
    },
    onSuccess: (conversation, { agentId }) => {
      const queryId = useAgentBuilderStore.getState().queryId
      queryClient.setQueryData(["baseline-chat", queryId, agentId], conversation)
    },
  })
}
