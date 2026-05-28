import { QueryProvider } from "@/components/common/query-provider"

import { AgentBuilderHeader } from "@/features/agent-builder/header"

export default function AgentBuilderLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <QueryProvider>
      <div className="flex h-screen w-full flex-col">
        <AgentBuilderHeader />
        <div className="flex-1 overflow-hidden">{children}</div>
      </div>
    </QueryProvider>
  )
}
