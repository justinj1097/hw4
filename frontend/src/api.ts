import type { ChatMessage, Checks, Facets, Filters, PageContext, ProductCard, ProductDetail, Showcase, User } from './types'

const TOKEN_KEY = 'cc_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string | null) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let message = `Something went wrong (${res.status}).`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, '')).join(' ')
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(res.status, message)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export function fetchProducts(f: Filters) {
  const params = new URLSearchParams()
  if (f.q) params.set('q', f.q)
  if (f.category) params.set('category', f.category)
  if (f.color) params.set('color', f.color)
  if (f.size) params.set('size', f.size)
  if (f.inStock) params.set('in_stock', 'true')
  params.set('sort', f.sort)
  return request<{ products: ProductCard[]; total: number }>(`/api/products?${params}`)
}

/** Current cards for specific products (the Saved page), in the given order. */
export const fetchProductsByIds = (ids: string[]) =>
  request<{ products: ProductCard[]; total: number }>(`/api/products?ids=${encodeURIComponent(ids.join(','))}`)

export const fetchProduct = (id: string) => request<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)
export const fetchFacets = () => request<Facets>('/api/facets')

interface AuthResponse {
  token: string
  user: User
}
export const signup = (body: { first_name: string; last_name: string; email: string; password: string; confirm_password: string }) =>
  request<AuthResponse>('/api/auth/signup', { method: 'POST', body: JSON.stringify(body) })
export const login = (body: { email: string; password: string }) =>
  request<AuthResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) })
export const fetchMe = () => request<User>('/api/auth/me')

export const sendChat = (message: string, history: { role: string; content: string }[], page: PageContext) =>
  request<{ reply: string; showcase: Showcase | null; checks: Checks | null; effort: 'low' | 'high' }>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history, page }),
  })

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const rows = await request<{ id: number; role: 'user' | 'assistant'; content: string; showcase: Showcase | null; checks: Checks | null }[]>('/api/chat/history')
  return rows.map((r) => ({ id: `db-${r.id}`, role: r.role, content: r.content, showcase: r.showcase, checks: r.checks }))
}
export const clearChatHistory = () => request<void>('/api/chat/history', { method: 'DELETE' })
