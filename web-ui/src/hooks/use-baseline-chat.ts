"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import {
  BaselineConversationSchema,
  type BaselineConversation,
} from "@/types/baseline"

async function fetchConversation(queryId: string): Promise<BaselineConversation> {
  return fetcher(
    `/api/query/${queryId}/baseline-chat`,
    BaselineConversationSchema,
  )
}

export function useBaselineChat() {
  const queryId = useAgentBuilderStore((state) => state.queryId)
  const debateStage = useAgentBuilderStore(
    (state) => state.pipelineStages.debate,
  )
  return useQuery({
    queryKey: ["baseline-chat", queryId],
    queryFn: () => fetchConversation(queryId!),
    enabled: !!queryId && debateStage === "complete",
    staleTime: Infinity,
    gcTime: Infinity,
  })
}

export function useSendBaselineMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      message,
      agentIds,
    }: {
      message: string
      agentIds: number[]
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
            agent_ids: agentIds.map(String),
          }),
        },
      )
    },
    onSuccess: (conversation) => {
      const queryId = useAgentBuilderStore.getState().queryId
      queryClient.setQueryData(["baseline-chat", queryId], conversation)
    },
  })
}
