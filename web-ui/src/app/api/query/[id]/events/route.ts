import { upstream } from "@/lib/api/upstream"

export async function GET(
  _: Request,
  ctx: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await ctx.params
  const res = await upstream(`/api/v1/queries/${id}/events`, { method: "GET" })
  return new Response(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  })
}
