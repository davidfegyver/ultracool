import A, { type Aladin } from 'aladin-lite'
import { useEffect, useRef } from 'react'
import type { Frame, Sequence } from '../api'
import { LayerRow } from './LayersPanel'

export const ALL_BANDS = ['W1', 'W2', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
const SKY_LAYER = 'Flipbook frame'

export type Flipbook = {
  bands: string[]
  hideFlagged: boolean
  excluded: Set<string>
  frameId: string | null
  playing: boolean
  fps: number
  showOnSky: boolean
}

/** Frames passing the band + flag filters (the rows of the layers panel). */
export const filterFrames = (seq: Sequence | null, fb: Flipbook) =>
  (seq?.frames ?? []).filter((f) => fb.bands.includes(f.band) && !(fb.hideFlagged && f.flagged))

type Props = {
  seq: Sequence | null
  fb: Flipbook
  set: (patch: Partial<Flipbook>) => void
  aladin: Aladin | null
  /** URL of an image to show instead of the current frame (diff/stack), or null. */
  override?: { png: string; label: string } | null
  children?: React.ReactNode
}

export default function Player({ seq, fb, set, aladin, override, children }: Props) {
  const playable = filterFrames(seq, fb).filter((f) => !fb.excluded.has(f.id))
  const idx = Math.max(0, playable.findIndex((f) => f.id === fb.frameId))
  const cur: Frame | undefined = playable[idx]

  const step = (d: number) => {
    if (!playable.length) return
    set({ frameId: playable[(idx + d + playable.length) % playable.length].id })
  }
  // latest step without restarting the timer every render
  const stepRef = useRef(step)
  stepRef.current = step

  useEffect(() => {
    if (!fb.playing) return
    const t = setInterval(() => stepRef.current(1), 1000 / fb.fps)
    return () => clearInterval(t)
  }, [fb.playing, fb.fps])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return
      if (e.key === ' ') {
        e.preventDefault()
        set({ playing: !fb.playing })
      } else if (e.key === 'ArrowLeft') {
        set({ playing: false })
        stepRef.current(-1)
      } else if (e.key === 'ArrowRight') {
        set({ playing: false })
        stepRef.current(1)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [fb.playing, set])

  const shownPng = override?.png ?? cur?.png
  useEffect(() => {
    if (!aladin || !seq) return
    if (fb.showOnSky && shownPng) {
      aladin.setOverlayImageLayer(A.image(shownPng, { wcs: seq.grid.wcs, imgFormat: 'png', name: SKY_LAYER }), SKY_LAYER)
    } else {
      aladin.removeImageLayer(SKY_LAYER)
    }
  }, [aladin, seq?.id, shownPng, fb.showOnSky]) // eslint-disable-line react-hooks/exhaustive-deps

  const busy = seq && (seq.status === 'querying' || seq.status === 'fetching')
  return (
    <div className="space-y-2 p-2 text-xs">
      {seq?.status === 'error' && <p className="text-red-400">{seq.error}</p>}
      {busy && (
        <div>
          <div className="mb-1 text-slate-400">
            {seq.status === 'querying' ? 'Querying IRSA archive…' : `Fetching frames ${seq.done}/${seq.total}`}
          </div>
          <div className="h-1.5 rounded bg-slate-700">
            <div className="h-1.5 rounded bg-sky-500" style={{ width: `${seq.total ? (100 * seq.done) / seq.total : 3}%` }} />
          </div>
        </div>
      )}
      <div className="relative mx-auto h-[360px] w-[360px] bg-black">
        {shownPng && seq ? (
          <>
            <img src={shownPng} alt={override?.label ?? `Frame ${cur?.date}`} className="h-full w-full [image-rendering:pixelated]" />
            {!override && cur && (
              <svg viewBox={`0 0 ${seq.grid.width} ${seq.grid.height}`} className="pointer-events-none absolute inset-0 h-full w-full">
                <circle cx={cur.target_px[0] + 0.5} cy={cur.target_px[1] + 0.5} r={5} fill="none" stroke="#f472b6" strokeWidth={0.6} />
              </svg>
            )}
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-500">{seq ? 'No frames match the filters' : 'No sequence'}</div>
        )}
      </div>
      <div className="flex h-5 items-center gap-2">
        {override ? (
          <span>{override.label}</span>
        ) : (
          cur && (
            <>
              <span>{cur.date.slice(0, 10)}</span>·<span>{cur.survey === 'wise' ? 'WISE' : 'SPHEREx'}</span>·<span>{cur.band}</span>·
              <span>{cur.wavelength_um?.toFixed(2)} µm</span>
              {cur.flagged && <span className="rounded bg-amber-700 px-1">flagged</span>}
            </>
          )
        )}
        <span className="ml-auto text-slate-500">{playable.length ? `${idx + 1}/${playable.length}` : ''}</span>
      </div>
      <div className="flex items-center gap-1">
        <button className="rounded bg-slate-700 px-2 py-1" aria-label="Previous frame" onClick={() => { set({ playing: false }); step(-1) }}>⏮</button>
        <button className="w-16 rounded bg-sky-700 px-2 py-1" onClick={() => set({ playing: !fb.playing })}>{fb.playing ? '⏸ Pause' : '▶ Play'}</button>
        <button className="rounded bg-slate-700 px-2 py-1" aria-label="Next frame" onClick={() => { set({ playing: false }); step(1) }}>⏭</button>
        <input
          aria-label="Scrub"
          type="range"
          className="flex-1"
          min={0}
          max={Math.max(0, playable.length - 1)}
          value={idx}
          onChange={(e) => set({ playing: false, frameId: playable[Number(e.target.value)]?.id ?? null })}
        />
        <select aria-label="Frames per second" className="rounded bg-slate-800 px-1 py-1" value={fb.fps} onChange={(e) => set({ fps: Number(e.target.value) })}>
          {[0.5, 1, 2, 4].map((f) => <option key={f} value={f}>{f} fps</option>)}
        </select>
      </div>
      <div className="flex flex-wrap gap-1">
        {ALL_BANDS.map((b) => {
          const on = fb.bands.includes(b)
          return (
            <button
              key={b}
              aria-pressed={on}
              className={`rounded px-2 py-0.5 ${on ? 'bg-sky-700' : 'bg-slate-800 text-slate-400'}`}
              onClick={() => set({ bands: on ? fb.bands.filter((x) => x !== b) : [...fb.bands, b] })}
            >
              {b}
            </button>
          )
        })}
      </div>
      <div className="flex gap-3">
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={fb.hideFlagged} onChange={(e) => set({ hideFlagged: e.target.checked })} /> Hide flagged frames
          {fb.hideFlagged && seq && (
            <span className="text-slate-500">
              ({seq.frames.filter((f) => f.flagged && fb.bands.includes(f.band)).length} hidden)
            </span>
          )}
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={fb.showOnSky} onChange={(e) => set({ showOnSky: e.target.checked })} /> Show on sky
        </label>
      </div>
      {children}
    </div>
  )
}

/** "Flipbook frames" group rows: eye = include in playback, click = pause on that frame. */
export function FrameRows({ seq, fb, set }: { seq: Sequence | null; fb: Flipbook; set: (p: Partial<Flipbook>) => void }) {
  const rows = useRef(new Map<string, HTMLDivElement>())
  const frames = filterFrames(seq, fb)
  useEffect(() => {
    if (!fb.playing && fb.frameId) rows.current.get(fb.frameId)?.scrollIntoView({ block: 'nearest' })
  }, [fb.playing, fb.frameId])
  if (!frames.length) return <p className="px-2 py-1 text-xs text-slate-500">No frames yet</p>
  return (
    <div className="max-h-72 overflow-y-auto">
      {frames.map((f) => (
        <LayerRow
          key={f.id}
          rowRef={(el) => (el ? rows.current.set(f.id, el) : rows.current.delete(f.id))}
          selected={f.id === fb.frameId}
          on={!fb.excluded.has(f.id)}
          onToggle={() => {
            const ex = new Set(fb.excluded)
            if (ex.has(f.id)) ex.delete(f.id)
            else ex.add(f.id)
            set({ excluded: ex })
          }}
          onClick={() => set({ playing: false, frameId: f.id })}
          label={
            <span className="flex items-center gap-2">
              <img src={f.png} alt="" className="h-6 w-6 [image-rendering:pixelated]" loading="lazy" />
              <span>{f.date.slice(0, 10)}</span>
              <span className="text-slate-400">{f.band}</span>
              <span className="text-slate-500">{f.wavelength_um?.toFixed(2)} µm</span>
              {f.flagged && <span className="text-amber-500">⚑</span>}
            </span>
          }
        />
      ))}
    </div>
  )
}
