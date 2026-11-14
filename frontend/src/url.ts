export const MODES = ['learn', 'explore', 'research', 'discover'] as const
export type Mode = (typeof MODES)[number]

export type UrlState = {
  mode: Mode | null
  lesson: string | null
  target: string | null
  ra: number | null
  dec: number | null
  fov: number | null
  frame: string | null
  bands: string[] | null
  /** probe point (ra, dec at epoch 2000) and its adopted proper motion (mas/yr) */
  probe: [number, number] | null
  probe_pm: [number, number] | null
}

const num = (v: string | null) => (v === null || v === '' || isNaN(Number(v)) ? null : Number(v))
const pair = (v: string | null) => {
  const xs = (v ?? '').split(',').map(num)
  return xs.length === 2 && xs[0] !== null && xs[1] !== null ? ([xs[0], xs[1]] as [number, number]) : null
}

export function readUrl(): UrlState {
  const p = new URLSearchParams(location.search)
  const mode = p.get('mode') as Mode | null
  return {
    mode: mode && MODES.includes(mode) ? mode : null,
    lesson: p.get('lesson'),
    target: p.get('target'),
    ra: num(p.get('ra')),
    dec: num(p.get('dec')),
    fov: num(p.get('fov')),
    frame: p.get('frame'),
    bands: p.get('bands') ? p.get('bands')!.split(',') : null,
    probe: pair(p.get('probe')),
    probe_pm: pair(p.get('probe_pm')),
  }
}

/** Set (string) or delete (null) query params; replaces the history entry unless `push` (mode switches, so Back works). */
export function writeUrl(patch: Record<string, string | null>, push = false) {
  const p = new URLSearchParams(location.search)
  for (const [k, v] of Object.entries(patch)) {
    if (v === null) p.delete(k)
    else p.set(k, v)
  }
  history[push ? 'pushState' : 'replaceState'](null, '', `${location.pathname}?${p}`)
}
