import { useCallback, useEffect, useRef, useState } from 'react'
import { getSequence, isMissing, resolveTarget, startSequence, type Resolved, type SeqOptions, type Sequence } from './api'
import type { Flipbook } from './components/Player'
import { readUrl, writeUrl } from './url'

export const DEFAULT_TARGET = "Barnard's Star"

/** Target from the URL (ra/dec, else name, else the default), name lookups, and URL sync. */
export function useTarget() {
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const lookup = async (q: string) => {
    setBusy(true)
    setError(null)
    try {
      setResolved(await resolveTarget(q))
      writeUrl({ target: q, ra: null, dec: null })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  /** jump to a known position (catalog row, random field); pm 0 unless given */
  const goTo = (r: Resolved) => {
    writeUrl({ target: r.name, ra: r.ra.toFixed(6), dec: r.dec.toFixed(6), frame: null })
    setResolved(r)
  }

  useEffect(() => {
    const { ra, dec, target } = readUrl()
    if (ra !== null && dec !== null) {
      setResolved({ name: target, ra, dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: null })
    } else {
      lookup(target ?? DEFAULT_TARGET)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { resolved, lookup, goTo, busy, error, setError }
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
    excluded: new Set(),
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
 * is in, if the backend reports `wise_done`). 404 = backend without that endpoint yet.
 * `busy`: still waiting (frames or the request), so callers can show a spinner next to `note`. */
export function useSeqResult<T>(seq: Sequence | null, fetcher: (id: string) => Promise<T>, afterWise = false) {
  const [state, setState] = useState<{ id: string; data: T | null; note: string | null; busy: boolean } | null>(null)
  const ready = seq && (seq.status === 'done' || (afterWise && seq.wise_done)) ? seq.id : null
  useEffect(() => {
    if (!ready) return
    let stale = false
    // first summary call queries IRSA and SkyBoT (25-45 s); no client timeout, just say what is happening
    setState({ id: ready, data: null, note: 'Asking the archives… (the first look at a field can take up to a minute)', busy: true })
    fetcher(ready)
      .then((data) => !stale && setState({ id: ready, data, note: null, busy: false }))
      .catch((e) => !stale && setState({ id: ready, data: null, note: isMissing(e) ? 'Not available yet on this server' : (e as Error).message, busy: false }))
    return () => {
      stale = true
    }
  }, [ready]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!seq) return { data: null, note: null, busy: false }
  if (seq.status === 'error') return { data: null, note: 'Sequence failed', busy: false }
  if (!ready || state?.id !== ready) return { data: null, note: afterWise ? 'Waiting for the WISE frames…' : 'Waiting for all frames…', busy: true }
  return state
}
