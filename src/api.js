import { auth, logout } from './auth'

export async function api(path, { method = 'GET', body, params } = {}) {
  let url = '/api' + path
  if (params) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    if ([...qs].length) url += '?' + qs
  }
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`

  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  let data = {}
  try { data = await res.json() } catch { /* non-JSON response */ }
  if (!res.ok) {
    if (res.status === 401 && auth.token) {
      logout()
      window.location.href = '/login'
    }
    throw new Error(data.error || 'Request failed')
  }
  return data
}

// Download a file that needs the auth header (e.g. CSV export)
export async function downloadFile(path, filename) {
  const res = await fetch('/api' + path, { headers: { Authorization: `Bearer ${auth.token}` } })
  if (!res.ok) throw new Error('Download failed')
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
