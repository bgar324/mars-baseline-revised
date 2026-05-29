import { proxy } from "@/lib/api/upstream"

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string; cycleId: string }> },
) {
  const { id, cycleId } = await params
  const body = await request.text()
  return proxy(`/api/v1/debates/${id}/cycles/${cycleId}/steers`, {
    method: "PUT",
    body,
  })
}
