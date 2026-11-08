// Minimal fetch wrapper.
// - Access token lives only in memory (never localStorage) to limit XSS impact.
// - Refresh token is an httpOnly cookie set by the API; we call /auth/refresh/
//   transparently on 401 and retry once.
const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

let accessToken = null
let refreshing = null
let onAuthLost = () => {}

export function setAccessToken(token) {
  accessToken = token
}
export function hasAccessToken() {
  return !!accessToken
}
export function setAuthLostHandler(fn) {
  onAuthLost = fn
}

export class ApiError extends Error {
  constructor(status, data) {
    super(formatError(data) || `Request failed (${status})`)
    this.status = status
    this.data = data || {}
  }
  field(name) {
    const v = this.data?.[name]
    return Array.isArray(v) ? v.join(' ') : v || ''
  }
}

function formatError(data) {
  if (!data) return ''
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  if (data.non_field_errors) return data.non_field_errors.join(' ')
  const first = Object.entries(data)[0]
  if (!first) return ''
  const [key, val] = first
  const msg = Array.isArray(val) ? val.join(' ') : String(val)
  return key === 'non_field_errors' ? msg : `${key.replace(/_/g, ' ')}: ${msg}`
}

export async function refreshAccessToken() {
  if (!refreshing) {
    refreshing = fetch(`${BASE}/api/auth/refresh/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
    })
      .then(async (res) => {
        if (!res.ok) {
          accessToken = null
          return false
        }
        accessToken = (await res.json()).access
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

export async function api(path, { method = 'GET', body, auth = true, retry = true, query } = {}) {
  const headers = { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`

  let url = `${BASE}/api${path}`
  if (query) {
    const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== '' && v != null))
    if ([...qs].length) url += `?${qs}`
  }

  const res = await fetch(url, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401 && auth && retry) {
    if (await refreshAccessToken()) return api(path, { method, body, auth, retry: false, query })
    onAuthLost()
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}
