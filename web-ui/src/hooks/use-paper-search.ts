"use client"

import { useEffect, useRef, useState } from "react"

import { fetcher } from "@/lib/api/client"
import { PaperListSchema, type Paper } from "@/types/paper"

export const PAPER_SEARCH_PAGE_SIZE = 10
export const PAPER_SEARCH_MAX_RESULTS = 50

async function searchPaperPage(
  query: string,
  limit: number,
  offset: number,
  signal: AbortSignal,
): Promise<Paper[]> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  })
  return fetcher(
    `/api/paper-search?${params}`,
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
  const [error, setError] = useState<Error | null>(null)
  const requestId = useRef(0)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => () => controller.current?.abort(), [])

  const mutate = async (query: string) => {
    controller.current?.abort()
    const activeController = new AbortController()
    controller.current = activeController
    const activeRequest = ++requestId.current

    setData(undefined)
    setError(null)
    setIsPending(true)

    try {
      const papers = await searchPaperPage(
        query,
        PAPER_SEARCH_MAX_RESULTS,
        0,
        activeController.signal,
      )
      if (activeRequest !== requestId.current) return
      setData([
        ...new Map(papers.map((paper) => [paper.id, paper])).values(),
      ])
    } catch (searchError) {
      if (activeController.signal.aborted) return
      setError(asError(searchError))
    } finally {
      if (activeRequest === requestId.current) setIsPending(false)
    }
  }

  return { data, error, isPending, mutate }
}
