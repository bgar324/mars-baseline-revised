import { proxy } from "@/lib/api/upstream"

export async function GET(request: Request) {
  const search = new URL(request.url).searchParams
  return proxy(`/api/v1/queries/paper-search?${search}`)
}
