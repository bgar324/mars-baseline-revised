import { proxy } from "@/lib/api/upstream"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  return proxy(`/api/v1/queries/${id}/debate`)
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const body = await request.text()
  return proxy(`/api/v1/queries/${id}/debate`, { method: "POST", body })
}
