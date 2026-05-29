import { proxy } from "@/lib/api/upstream"

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string; cycleId: string }> },
) {
  const { id, cycleId } = await params
  return proxy(`/api/v1/debates/${id}/cycles/${cycleId}/run`, {
    method: "POST",
  })
}
