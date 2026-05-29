import { proxy } from "@/lib/api/upstream"

export async function POST(request: Request) {
  const body = await request.text()
  return proxy("/api/v1/debates", { method: "POST", body })
}
