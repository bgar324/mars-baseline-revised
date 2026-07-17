"use client"

import { useEffect, useRef, useState } from "react"

import { fetcher } from "@/lib/api/client"
import { useAgentBuilderStore } from "@/store/agent-builder"
import { PaperListSchema, type Paper } from "@/types/paper"

export const PAPER_SEARCH_PAGE_SIZE = 10
export const PAPER_SEARCH_MAX_RESULTS = 50

async function searchPaperPage(
  queryId: string,
  query: string,
  offset: number,
  signal: AbortSignal,
): Promise<Paper[]> {
  const params = new URLSearchParams({
    q: query,
    limit: String(PAPER_SEARCH_PAGE_SIZE),
    offset: String(offset),
  })
  return fetcher(
    `/api/query/${queryId}/paper-search?${params}`,
    PaperListSchema,
    { signal },
  )
}

function asError(error: unknown): Error {
  return error instanceof Error ? error : new Error("Paper search failed")
}

export function usePaperSearch() {
  const [data, setData] = useState<Paper[]>()
  const [isPending, setIsPending] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const requestId = useRef(0)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => () => controller.current?.abort(), [])

  const mutate = async (query: string) => {
    const queryId = useAgentBuilderStore.getState().queryId
    if (!queryId) {
      setError(new Error("no active query"))
      return
    }

    controller.current?.abort()
    const activeController = new AbortController()
    controller.current = activeController
    const activeRequest = ++requestId.current

    setData(undefined)
    setError(null)
    setIsLoadingMore(false)
    setIsPending(true)

    let firstPage: Paper[]
    try {
      firstPage = await searchPaperPage(
        queryId,
        query,
        0,
        activeController.signal,
      )
    } catch (searchError) {
      if (activeController.signal.aborted) return
      setError(asError(searchError))
      setIsPending(false)
      return
    }

    if (activeRequest !== requestId.current) return
    setData(firstPage)
    setIsPending(false)

    if (firstPage.length < PAPER_SEARCH_PAGE_SIZE) return
    setIsLoadingMore(true)

    try {
      for (
        let offset = PAPER_SEARCH_PAGE_SIZE;
        offset < PAPER_SEARCH_MAX_RESULTS;
        offset += PAPER_SEARCH_PAGE_SIZE
      ) {
        const page = await searchPaperPage(
          queryId,
          query,
          offset,
          activeController.signal,
        )
        if (activeRequest !== requestId.current) return
        setData((current) => [
          ...new Map(
            [...(current ?? []), ...page].map((paper) => [paper.id, paper]),
          ).values(),
        ])
        if (page.length < PAPER_SEARCH_PAGE_SIZE) break
      }
    } catch (searchError) {
      if (!activeController.signal.aborted) {
        console.warn("[paper-search] background fetch stopped", searchError)
      }
    } finally {
      if (activeRequest === requestId.current) setIsLoadingMore(false)
    }
  }

  return { data, error, isPending, isLoadingMore, mutate }
}
