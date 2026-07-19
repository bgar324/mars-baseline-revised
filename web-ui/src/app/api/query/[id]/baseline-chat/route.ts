import { proxy } from "@/lib/api/upstream"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const agentId = new URL(request.url).searchParams.get("agent_id")
  const search = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ""
  return proxy(`/api/v1/queries/${id}/baseline-chat${search}`)
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const body = await request.text()
  return proxy(`/api/v1/queries/${id}/baseline-chat`, {
    method: "POST",
    body,
  })
}
