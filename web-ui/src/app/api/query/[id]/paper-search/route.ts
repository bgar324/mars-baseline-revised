import { proxy } from "@/lib/api/upstream"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const search = new URL(request.url).searchParams
  return proxy(`/api/v1/queries/${id}/paper-search?${search}`)
}
