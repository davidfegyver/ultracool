import type { Aladin, Source } from 'aladin-lite'
import { useCallback, useEffect, useState } from 'react'
import { getSequence, resolveTarget, startSequence, ucdsNear, type Resolved, type Sequence, type Ucd } from './api'
import Catalogs from './components/Catalogs'
import LayersPanel from './components/LayersPanel'
import Player, { FrameRows, StackRows, type Flipbook } from './components/Player'
import PlotsPanel from './components/PlotsPanel'
import SkyView from './components/SkyView'
import SelectionTable from './components/SelectionTable'
import TargetBar from './components/TargetBar'
import UcdSearch from './components/UcdSearch'
import { readUrl, writeUrl } from './url'

const initialUrl = readUrl()
const DEFAULT_TARGET = "Barnard's Star"

export default function App() {
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [busy, setBusy] = useState(false)
  // name put into the target box from outside (UCD table click); remounts TargetBar with it
  const [picked, setPicked] = useState<string | null>(null)
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
  const [known, setKnown] = useState<Ucd | null>(null)
  const [skyUcds, setSkyUcds] = useState<Ucd[]>([])
  const [spiffOn, setSpiffOn] = useState(false)
  const [catalogCount, setCatalogCount] = useState(0)
  const [fov, setFov] = useState(initialUrl.fov ?? 0.25)
  const [selection, setSelection] = useState<Source[][] | null>(null)
  const [compareA, setCompareA] = useState<string | null>(null)
  const [stackBand, setStackBand] = useState<string | null>(null)

  const setFlipbook = useCallback((patch: Partial<Flipbook>) => {
    if (patch.frameId) setStackBand(null) // picking a frame leaves the stack view
    setFb((prev) => {
      const next = { ...prev, ...patch }
      if (patch.bands) writeUrl({ bands: next.bands.join(',') })
      // URL remembers the frame you stopped on, not every frame that plays past
      if (!next.playing && next.frameId && (patch.playing === false || patch.frameId)) writeUrl({ frame: next.frameId })
      return next
    })
  }, [])

  const frameById = (id: string | null) => seq?.frames.find((f) => f.id === id)
  const frameA = frameById(compareA)
  const frameB = compareA && fb.frameId !== compareA ? frameById(fb.frameId) : undefined
  const override =
    seq && frameA && frameB
      ? {
          png: `/api/sequences/${seq.id}/diff.png?a=${encodeURIComponent(frameA.id)}&b=${encodeURIComponent(frameB.id)}`,
          label: `Difference ${frameB.date.slice(0, 10)} ${frameB.band} − ${frameA.date.slice(0, 10)} ${frameA.band} (red = new, blue = old)`,
        }
      : seq && stackBand
        ? { png: `/api/sequences/${seq.id}/stack.png?band=${stackBand}&n=${seq.frames.length}`, label: `Median stack ${stackBand}` }
        : null
  const canSelect = catalogCount > 0 && fov < 0.5

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
    setCompareA(null)
    setStackBand(null)
    setSelection(null)
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

  useEffect(() => {
    setKnown(null)
    if (resolved) ucdsNear(resolved).then((r) => setKnown(r[0] ?? null)).catch(() => setKnown(null))
  }, [resolved])

  const pickUcd = (u: Ucd) => {
    setFlipbook({ frameId: null, playing: false, excluded: new Set() })
    writeUrl({ target: u.designation, ra: u.ra.toFixed(6), dec: u.dec.toFixed(6), frame: null })
    setPicked(u.designation)
    setResolved({ name: u.designation, ra: u.ra, dec: u.dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: u.spiff_autotype })
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <TargetBar
        key={picked}
        initial={picked ?? initialUrl.target ?? DEFAULT_TARGET}
        resolved={resolved}
        busy={busy}
        error={error}
        onSubmit={(q) => {
          setFlipbook({ frameId: null, playing: false, excluded: new Set() })
          writeUrl({ frame: null })
          lookup(q)
        }}
        badge={
          known && (
            <span className="rounded bg-fuchsia-900 px-2 py-0.5 text-xs">
              Known UCD: {known.spiff_autotype} (SPIFF){known.literature_spectral_type && `, lit. ${known.literature_spectral_type}`}
            </span>
          )
        }
      />
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="relative min-h-0 flex-1">
            {resolved && (
              // grid centre = 2018 position, so high-PM stars sit in the middle of the flipbook overlay
              <SkyView
                ra={seq ? Number(seq.grid.wcs.CRVAL1) : resolved.ra}
                dec={seq ? Number(seq.grid.wcs.CRVAL2) : resolved.dec}
                fov={initialUrl.fov ?? 0.25}
                onReady={setAladin}
                onFov={setFov}
              />
            )}
            <button
              className="absolute top-2 left-1/2 z-10 -translate-x-1/2 rounded bg-slate-800/90 px-2 py-1 text-xs enabled:hover:bg-slate-700 disabled:text-slate-500"
              disabled={!canSelect}
              title="Drag a rectangle to list catalog sources inside it. Needs at least one visible catalog layer and a field of view under 0.5°."
              onClick={() => aladin?.select('rect', (_shape, groups) => setSelection(groups))}
            >
              ⬚ Select region
            </button>
            {selection && <SelectionTable groups={selection} onClose={() => setSelection(null)} />}
          </div>
          <div className="flex h-72 shrink-0 border-t border-slate-700 bg-slate-900">
            <div className="min-w-0 flex-1">
              <PlotsPanel seq={seq} />
            </div>
            <div className="w-[30rem] shrink-0 border-l border-slate-700">
              <UcdSearch
                onPick={pickUcd}
                onShowOnSky={(rows) => {
                  setSkyUcds(rows)
                  setSpiffOn(true)
                }}
              />
            </div>
          </div>
        </div>
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-slate-700 bg-slate-900">
          <Player seq={seq} fb={fb} set={setFlipbook} aladin={aladin} override={override}>
            {(cur) => (
              <div className="flex items-center gap-2">
                <button
                  className={`rounded px-2 py-1 ${compareA ? 'bg-amber-700' : 'bg-slate-700'}`}
                  disabled={!compareA && !cur}
                  onClick={() => {
                    setStackBand(null)
                    setCompareA(compareA ? null : (cur?.id ?? null))
                  }}
                >
                  {compareA ? 'Clear compare' : 'Compare'}
                </button>
                <span className="text-slate-500">
                  {compareA ? (frameB ? '' : `A = ${frameA?.date.slice(0, 10)} ${frameA?.band}; pick frame B`) : 'Pin the current frame as A'}
                </span>
              </div>
            )}
          </Player>
          <LayersPanel
            aladin={aladin}
            frames={
              <>
                <FrameRows seq={seq} fb={fb} set={setFlipbook} />
                <StackRows
                  seq={seq}
                  band={stackBand}
                  onPick={(b) => {
                    setCompareA(null)
                    setFlipbook({ playing: false })
                    setStackBand(b)
                  }}
                />
              </>
            }
            catalogs={
              aladin && (
                <Catalogs aladin={aladin} ucds={skyUcds} spiffOn={spiffOn} setSpiffOn={setSpiffOn} onVisibleCount={setCatalogCount} />
              )
            }
          />
        </aside>
      </div>
    </div>
  )
}
