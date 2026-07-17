import type { Metadata } from "next"

import { QueryProvider } from "@/components/common/query-provider"

export const metadata: Metadata = {
  title: "Research Discussion | MARS Baseline",
  other: { "study-condition": "baseline" },
}

export default function BaselineLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <QueryProvider>{children}</QueryProvider>
}
