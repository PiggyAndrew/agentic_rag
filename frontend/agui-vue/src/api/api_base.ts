export function getApiBase(): string {
  const runtimeValue =
    typeof window !== 'undefined' &&
    (window as any)?.runtime &&
    typeof (window as any).runtime.getApiBase === 'function'
      ? String((window as any).runtime.getApiBase() || '')
      : ''

  const raw =
    runtimeValue ||
    (import.meta as any).env?.VITE_API_BASE ||
    (import.meta as any).env?.VITE_API_URL ||
    'http://localhost:8000'

  let s = String(raw || '').trim()
  if (!s) s = 'http://localhost:8000'
  if (s.endsWith('/api/chat')) s = s.slice(0, -'/api/chat'.length)
  return s.replace(/\/+$/, '')
}

export function joinApiUrl(path: string): string {
  const base = getApiBase()
  const p = String(path || '')
  if (!p) return base
  if (p.startsWith('/')) return `${base}${p}`
  return `${base}/${p}`
}

