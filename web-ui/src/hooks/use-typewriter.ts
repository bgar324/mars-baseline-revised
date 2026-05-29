"use client"

import { useEffect, useState } from "react"

const CHARS_PER_TICK = 2
const TICK_MS = 24

export function useTypewriter(text: string, isAnimating: boolean): string {
  const [revealed, setRevealed] = useState(text)

  useEffect(() => {
    if (!isAnimating) {
      setRevealed(text)
      return
    }
    setRevealed((prev) => (text.startsWith(prev) ? prev : ""))
    const id = setInterval(() => {
      setRevealed((prev) =>
        prev.length >= text.length
          ? prev
          : text.slice(0, prev.length + CHARS_PER_TICK),
      )
    }, TICK_MS)
    return () => clearInterval(id)
  }, [text, isAnimating])

  return revealed
}
