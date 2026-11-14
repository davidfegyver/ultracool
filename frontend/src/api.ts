export type Resolved = {
  name: string | null
  ra: number
  dec: number
  pmra_masyr: number
  pmdec_masyr: number
  epoch_yr: number
  otype: string | null
  sptype: string | null
}

async function get<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new Error(body?.detail ?? `${r.status} ${r.statusText}`)
  }
  return r.json()
}

const qs = (params: Record<string, string | number | null | undefined>) =>
  new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== null && v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)]),
  ).toString()

export const resolveTarget = (q: string) => get<Resolved>(`/api/resolve?${qs({ q })}`)
