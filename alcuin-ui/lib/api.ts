export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
export const GATEWAY_API_KEY = process.env.NEXT_PUBLIC_GATEWAY_API_KEY ?? ""

export const tokens = {
  get access()   { return typeof window !== "undefined" ? localStorage.getItem("access_token") : null },
  get refresh()  { return typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null },
  get username() { return typeof window !== "undefined" ? localStorage.getItem("auth_username") : null },
  set(access: string, refresh: string, username: string) {
    localStorage.setItem("access_token",  access)
    localStorage.setItem("refresh_token", refresh)
    localStorage.setItem("auth_username", username)
  },
  clear() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("auth_username")
  },
}

export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "X-API-Key": GATEWAY_API_KEY,
    ...(options.headers as Record<string, string> ?? {}),
  }
  if (tokens.access) headers["Authorization"] = `Bearer ${tokens.access}`

  let resp = await fetch(`${API_BASE}${url}`, { ...options, headers })

  if (resp.status === 401 && tokens.refresh) {
    const refreshResp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
      body: JSON.stringify({ refresh_token: tokens.refresh }),
    })
    if (refreshResp.ok) {
      const data = await refreshResp.json()
      tokens.set(data.access_token, data.refresh_token, tokens.username ?? "")
      headers["Authorization"] = `Bearer ${data.access_token}`
      resp = await fetch(`${API_BASE}${url}`, { ...options, headers })
    } else {
      tokens.clear()
    }
  }
  return resp
}
