import { QueryProvider } from "@/components/common/query-provider"

export default function CanvasLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <QueryProvider>{children}</QueryProvider>
}
