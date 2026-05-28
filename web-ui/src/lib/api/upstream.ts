const API_URL = process.env.API_URL ?? "http://localhost:8000"

export async function upstream(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const url = `${API_URL}${path}`
  return fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
}

export async function proxy(path: string, init?: RequestInit): Promise<Response> {
  try {
    const res = await upstream(path, init)
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : "upstream unreachable"
    return new Response(JSON.stringify({ detail: message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    })
  }
}
