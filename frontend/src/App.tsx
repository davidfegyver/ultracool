import type { Aladin } from 'aladin-lite'
import { useCallback, useEffect, useState } from 'react'
import { getSequence, resolveTarget, startSequence, type Resolved, type Sequence } from './api'
import LayersPanel from './components/LayersPanel'
import Player, { FrameRows, type Flipbook } from './components/Player'
import SkyView from './components/SkyView'
import TargetBar from './components/TargetBar'
import { readUrl, writeUrl } from './url'

const initialUrl = readUrl()
const DEFAULT_TARGET = "Barnard's Star"

export default function App() {
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aladin, setAladin] = useState<Aladin | null>(null)
  const [seq, setSeq] = useState<Sequence | null>(null)
  const [fb, setFb] = useState<Flipbook>({
    bands: initialUrl.bands ?? ['W2', 'D6'],
    hideFlagged: true,
    excluded: new Set(),
    frameId: initialUrl.frame,
    playing: false,
    fps: 1,
    showOnSky: true,
  })

  const setFlipbook = useCallback((patch: Partial<Flipbook>) => {
    setFb((prev) => {
      const next = { ...prev, ...patch }
      if (patch.bands) writeUrl({ bands: next.bands.join(',') })
      // URL remembers the frame you stopped on, not every frame that plays past
      if (!next.playing && next.frameId && (patch.playing === false || patch.frameId)) writeUrl({ frame: next.frameId })
      return next
    })
  }, [])

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

  useEffect(() => {
    const { ra, dec, target } = initialUrl
    if (ra !== null && dec !== null) {
      setResolved({ name: target, ra, dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: null })
    } else {
      lookup(target ?? DEFAULT_TARGET)
    }
  }, [])

  // start the sequence for the resolved target and poll until it settles
  useEffect(() => {
    if (!resolved) return
    let stop = false
    let timer: number | undefined
    setSeq(null)
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
    startSequence(resolved)
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
  }, [resolved])

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <TargetBar
        initial={initialUrl.target ?? DEFAULT_TARGET}
        resolved={resolved}
        busy={busy}
        error={error}
        onSubmit={(q) => {
          setFlipbook({ frameId: null, playing: false, excluded: new Set() })
          writeUrl({ frame: null })
          lookup(q)
        }}
      />
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          {resolved && (
            // grid centre = 2018 position, so high-PM stars sit in the middle of the flipbook overlay
            <SkyView
              ra={seq ? Number(seq.grid.wcs.CRVAL1) : resolved.ra}
              dec={seq ? Number(seq.grid.wcs.CRVAL2) : resolved.dec}
              fov={initialUrl.fov ?? 0.25}
              onReady={setAladin}
            />
          )}
        </div>
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-slate-700 bg-slate-900">
          <Player seq={seq} fb={fb} set={setFlipbook} aladin={aladin} />
          <LayersPanel aladin={aladin} frames={<FrameRows seq={seq} fb={fb} set={setFlipbook} />} />
        </aside>
      </div>
    </div>
  )
}
