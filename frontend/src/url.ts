export type UrlState = {
  target: string | null
  ra: number | null
  dec: number | null
  fov: number | null
  frame: string | null
  bands: string[] | null
}

const num = (v: string | null) => (v === null || v === '' || isNaN(Number(v)) ? null : Number(v))

export function readUrl(): UrlState {
  const p = new URLSearchParams(location.search)
  return {
    target: p.get('target'),
    ra: num(p.get('ra')),
    dec: num(p.get('dec')),
    fov: num(p.get('fov')),
    frame: p.get('frame'),
    bands: p.get('bands') ? p.get('bands')!.split(',') : null,
  }
}

/** Set (string) or delete (null) query params without adding history entries. */
export function writeUrl(patch: Record<string, string | null>) {
  const p = new URLSearchParams(location.search)
  for (const [k, v] of Object.entries(patch)) {
    if (v === null) p.delete(k)
    else p.set(k, v)
  }
  history.replaceState(null, '', `${location.pathname}?${p}`)
}
