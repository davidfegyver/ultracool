import { useCallback, useEffect, useRef, useState } from 'react'
import { getProbe, getSequence, isMissing, resolveTarget, startSequence, waitText, type Probe, type ProbeMode, type Resolved, type SeqOptions, type Sequence } from './api'
import type { Flipbook } from './components/Player'
import { MJD_2000, MJD_2018, propagate, worldToPx } from './sky'
import { readUrl, writeUrl } from './url'

export const DEFAULT_TARGET = "Barnard's Star"

/** Phones: below Tailwind's `md` breakpoint (48rem), the same line as the `max-md:` classes. */
export const PHONE_QUERY = '(max-width: 47.99rem)'

export function useIsPhone() {
  const [phone, setPhone] = useState(() => matchMedia(PHONE_QUERY).matches)
  useEffect(() => {
    const m = matchMedia(PHONE_QUERY)
    const on = () => setPhone(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return phone
}

/** Target from the URL (ra/dec with optional pm, else name, else `defaultTarget`), name lookups, and URL sync. */
export function useTarget(defaultTarget = DEFAULT_TARGET) {
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** resolve a name; `fallback` (e.g. a catalog row's position) is used when the resolver does not know it (404) */
  const lookup = async (q: string, fallback?: Resolved) => {
    setBusy(true)
    setError(null)
    try {
      setResolved(await resolveTarget(q))
      writeUrl({ target: q, ra: null, dec: null, pm: null })
    } catch (e) {
      if (fallback && isMissing(e)) goTo(fallback)
      else setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  /** jump to a known position (catalog row, random field, probe); pm 0 unless given */
  const goTo = (r: Resolved) => {
    const pm = r.pmra_masyr || r.pmdec_masyr ? `${r.pmra_masyr.toFixed(1)},${r.pmdec_masyr.toFixed(1)}` : null
    writeUrl({ target: r.name, ra: r.ra.toFixed(6), dec: r.dec.toFixed(6), pm, frame: null })
    setResolved(r)
  }

  useEffect(() => {
    const { ra, dec, target, pm } = readUrl()
    if (ra !== null && dec !== null) {
      setResolved({ name: target, ra, dec, pmra_masyr: pm?.[0] ?? 0, pmdec_masyr: pm?.[1] ?? 0, epoch_yr: 2000, otype: null, sptype: null })
    } else {
      lookup(target ?? defaultTarget)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { resolved, lookup, goTo, busy, error }
}

/** Start the sequence for a target and poll every 2 s until it settles. `priorityBands` (the bands on screen) are
 * processed first by the backend; they are read when the request is sent and never restart the sequence. */
export function useSequence(target: Resolved | null, opts: SeqOptions = {}, priorityBands?: string[]) {
  const [seq, setSeq] = useState<Sequence | null>(null)
  const [error, setError] = useState<string | null>(null)
  const optsKey = JSON.stringify(opts)
  const prio = useRef(priorityBands)
  prio.current = priorityBands
  useEffect(() => {
    setSeq(null)
    setError(null)
    if (!target) return
    let stop = false
    let timer: number | undefined
    const poll = async (id: string) => {
      try {
        const s = await getSequence(id)
        if (stop) return
        setSeq(s)
        if (s.status === 'done' || s.status === 'error') return
      } catch (e) {
        if (!stop) setError((e as Error).message)
      }
      timer = window.setTimeout(() => poll(id), 2000)
    }
    startSequence(target, { ...JSON.parse(optsKey), priority_bands: prio.current })
      .then(({ id }) => {
        if (!stop) poll(id)
      })
      .catch((e) => {
        if (!stop) setError((e as Error).message)
      })
    return () => {
      stop = true
      clearTimeout(timer)
    }
  }, [target, optsKey])
  return { seq, error }
}

/** Flipbook settings; bands and the frame you stop on are mirrored to the URL. */
export function useFlipbook(init: Partial<Flipbook> = {}) {
  const url = readUrl()
  const [fb, setFb] = useState<Flipbook>(() => ({
    bands: url.bands ?? ['W2', 'D6'],
    hideFlagged: true,
    frameId: url.frame,
    playing: false,
    fps: 1,
    showOnSky: true,
    deep: false,
    ...init,
  }))
  const set = useCallback((patch: Partial<Flipbook>) => {
    setFb((prev) => {
      const next = { ...prev, ...patch }
      if (patch.bands) writeUrl({ bands: next.bands.join(',') })
      // URL remembers the frame you stopped on, not every frame that plays past
      if (!next.playing && next.frameId && (patch.playing === false || patch.frameId)) writeUrl({ frame: next.frameId })
      return next
    })
  }, [])
  return [fb, set] as const
}

/** Result of a per-sequence endpoint, fetched once the sequence is done (with `afterWise`: as soon as every WISE frame
 * is in, `wise_done`).
 * `busy`: still waiting (frames or the request), so callers can show a spinner next to `note`. */
export function useSeqResult<T>(seq: Sequence | null, fetcher: (id: string) => Promise<T>, afterWise = false) {
  const [state, setState] = useState<{ id: string; data: T | null; note: string | null; busy: boolean } | null>(null)
  const ready = seq && (seq.status === 'done' || (afterWise && seq.wise_done)) ? seq.id : null
  useEffect(() => {
    if (!ready) return
    let stale = false
    // first summary call queries IRSA and SkyBoT (25-45 s); no client timeout, just say what is happening
    setState({ id: ready, data: null, note: "Querying NASA's archives. The first time anyone opens a field this can take a minute.", busy: true })
    fetcher(ready)
      .then((data) => !stale && setState({ id: ready, data, note: null, busy: false }))
      .catch((e) => !stale && setState({ id: ready, data: null, note: (e as Error).message, busy: false }))
    return () => {
      stale = true
    }
  }, [ready]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!seq) return { data: null, note: null, busy: false }
  if (seq.status === 'error') return { data: null, note: "Couldn't load the images for this field", busy: false }
  if (!ready || state?.id !== ready) {
    const wait = !ready && waitText(seq.queue_position, seq.eta_s)
    return { data: null, note: `${afterWise ? 'Waiting for the WISE images…' : 'Waiting for the images…'}${wait ? ` ${wait}` : ''}`, busy: true }
  }
  return state
}

/** Probe point: ICRS degrees at epoch 2000 plus an adopted proper motion (mas/yr). */
export type ProbePoint = { ra: number; dec: number; pmra_masyr: number; pmdec_masyr: number }
type ProbeResult = {
  /** last finished measurement */
  data: Probe | null
  /** point that `data` describes; differs from `point` once the probe is moved again */
  measuredAt: ProbePoint | null
  /** full measurement still running */
  progress: { done: number; total: number; queue_position?: number | null } | null
  busy: boolean
  error: string | null
}
export type ProbeCtl = ProbeResult & {
  sid: string | undefined
  /** the point lies outside the field (or within the photometry margin of its edge): measuring would be refused */
  outside: boolean
  point: ProbePoint | null
  place: (p: ProbePoint | null) => void
  /** screen position (client px) of the open action menu */
  menu: { x: number; y: number } | null
  setMenu: (m: { x: number; y: number } | null) => void
  measure: (mode: ProbeMode, p?: ProbePoint | null) => Promise<void>
}
const NO_RESULT: ProbeResult = { data: null, measuredAt: null, progress: null, busy: false, error: null }
// backend refuses points closer than 25" (~9 grid px) to the edge: the sky annulus must fit
const EDGE_MARGIN_PX = 9
/** set once the probe has been placed in this browser; the viewer's how-to hint goes away after that */
export const PROBE_USED_KEY = 'ultracool-probe-used'

/** The probe point (URL `probe`/`probe_pm`, restored without measuring), its action menu and its measurement on `seq`.
 * Moving the point never sends a request: only `measure` does. */
export function useProbe(seq: Sequence | null): ProbeCtl {
  const sid = seq?.id
  const [point, setPoint] = useState<ProbePoint | null>(() => {
    const u = readUrl()
    return u.probe && { ra: u.probe[0], dec: u.probe[1], pmra_masyr: u.probe_pm?.[0] ?? 0, pmdec_masyr: u.probe_pm?.[1] ?? 0 }
  })
  const pointRef = useRef(point)
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)
  const [result, setResult] = useState(NO_RESULT)
  const run = useRef(0) // bumping it abandons the running measurement's polls

  const place = useCallback((p: ProbePoint | null) => {
    pointRef.current = p
    if (p) localStorage.setItem(PROBE_USED_KEY, '1')
    setPoint(p)
    writeUrl({
      probe: p && `${p.ra.toFixed(6)},${p.dec.toFixed(6)}`,
      probe_pm: p && (p.pmra_masyr || p.pmdec_masyr) ? `${p.pmra_masyr.toFixed(1)},${p.pmdec_masyr.toFixed(1)}` : null,
    })
  }, [])

  // results belong to one sequence
  useEffect(() => {
    setResult(NO_RESULT)
    return () => {
      run.current++
    }
  }, [sid])

  const measure = async (mode: ProbeMode, p = pointRef.current) => {
    setMenu(null)
    if (!sid || !p) return
    const id = ++run.current
    setResult((r) => ({ ...r, busy: true, error: null, progress: null }))
    try {
      for (;;) {
        const d = await getProbe(sid, p, mode)
        if (id !== run.current) return
        if (d.status === 'error') throw new Error(d.error ?? 'Measurement failed')
        if (d.status === 'ok') {
          let at = p
          // the marker jumps to the snapped peak and takes the adopted pm, unless it was moved meanwhile
          if (pointRef.current === p) {
            at = { ...propagate(d.position.ra, d.position.dec, d.pm.pmra_masyr, d.pm.pmdec_masyr, d.pm.epoch_yr, MJD_2000), pmra_masyr: d.pm.pmra_masyr, pmdec_masyr: d.pm.pmdec_masyr }
            place(at)
          }
          setResult({ data: d, measuredAt: at, progress: null, busy: false, error: null })
          return
        }
        setResult((r) => ({ ...r, progress: { ...(d.progress ?? { done: 0, total: 0 }), queue_position: d.queue_position } }))
        await new Promise((ok) => setTimeout(ok, 3000)) // lib is ES2023: no Promise.withResolvers
        if (id !== run.current) return
      }
    } catch (e) {
      if (id === run.current) setResult((r) => ({ ...r, busy: false, progress: null, error: (e as Error).message }))
    }
  }

  let outside = true
  if (seq && point) {
    const q = propagate(point.ra, point.dec, point.pmra_masyr, point.pmdec_masyr, 2000, MJD_2018)
    const [x, y] = worldToPx(seq.grid.wcs, seq.grid.height, q.ra, q.dec)
    const m = EDGE_MARGIN_PX
    outside = !(x >= m && y >= m && x <= seq.grid.width - 1 - m && y <= seq.grid.height - 1 - m)
  }

  return { point, place, menu, setMenu, measure, ...result, sid, outside }
}
