export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(payload.detail || '请求失败', response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
