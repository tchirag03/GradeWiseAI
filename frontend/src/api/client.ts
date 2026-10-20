// ================================
// Centralized API Client
// ================================

const API_BASE = '/api'

/**
 * Thin wrapper around fetch() for JSON API calls.
 * Throws on non-ok responses with the server error message.
 */
async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(url, options)

  if (!res.ok) {
    let message = `Request failed: ${res.status}`
    try {
      const body = await res.json()
      message = body.detail || body.message || message
    } catch {
      // response wasn't JSON
    }
    throw new Error(message)
  }

  return res.json() as Promise<T>
}

/** GET helper */
export function get<T>(path: string): Promise<T> {
  return request<T>(`${API_BASE}${path}`)
}

/** POST helper (JSON body) */
export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
}

/** POST helper for file uploads (FormData) */
export function upload<T>(path: string, formData: FormData): Promise<T> {
  return request<T>(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type — browser sets it with boundary for multipart
  })
}

/** DELETE helper */
export function del<T>(path: string): Promise<T> {
  return request<T>(`${API_BASE}${path}`, { method: 'DELETE' })
}
