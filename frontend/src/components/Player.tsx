import A, { type Aladin } from 'aladin-lite'
import { useEffect, useRef, useState } from 'react'
import { waitText, type Frame, type Sequence } from '../api'
import { PROBE_USED_KEY, type ProbeCtl } from '../hooks'
import { APERTURE, mjdToIso, mjdToYear, PIX_ARCSEC, pxToWorld, type Mark } from '../sky'
import { ProbeDock, ProbeMarker } from './Probe'

export const ALL_BANDS = ['W1', 'W2', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
// wavelength coverage per band (µm): WISE filter centres; SPHEREx detector ranges as measured in our frames
const BAND_UM: Record<string, string> = {
  W1: '3.4', W2: '4.6', D1: '0.75–1.1', D2: '1.1–1.6', D3: '1.6–2.4', D4: '2.4–3.8', D5: '3.8–4.4', D6: '4.4–5.0',
}
const SKY_LAYER = 'Flipbook frame'
// media icons as SVG paths: the ⏮ ⏭ ⏸ glyphs are missing from common Chromium/Linux fonts and render as empty boxes
const ICON = { prev: 'M3 2h2v12H3zM14 2v12L6 8z', next: 'M11 2h2v12h-2zM2 2v12l8-6z', play: 'M4 2v12l10-6z', pause: 'M3 2h4v12H3zM9 2h4v12H9z' }
const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 16 16" className="h-3 w-3 fill-current" aria-hidden>
    <path d={d} />
  </svg>
)

export type Flipbook = {
  bands: string[]
  hideFlagged: boolean
  frameId: string | null
  playing: boolean
  fps: number
  showOnSky: boolean
  /** play multi-epoch deep stacks instead of single frames */
  deep: boolean
}

/** One deep stack per band and time window: WISE in 2-year windows (2010 alone), SPHEREx per ~6-month survey epoch.
 * Faint movers like WISEA J1534-1043 are invisible in single frames but show at 3-5 sigma here. */
function deepFrames(seq: Sequence, bands: string[]): Frame[] {
  const groups = new Map<string, Frame[]>()
  for (const f of seq.frames) {
    if (!bands.includes(f.band) || f.flagged) continue
    const year = Number(f.date.slice(0, 4))
    const win = f.survey === 'wise' ? (year < 2014 ? 2010 : 2014 + 2 * Math.floor((year - 2014) / 2)) : f.epoch_index
    const key = `${f.band}-${win}`
    groups.set(key, [...(groups.get(key) ?? []), f])
  }
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length
  return [...groups.entries()]
    .map(([key, fs]) => {
      const mjds = fs.map((f) => f.mjd)
      const mjd = mean(mjds)
      return {
        ...fs[0],
        id: `deep-${key}`,
        mjd,
        date: mjdToIso(mjd),
        wavelength_um: fs[0].wavelength_um === null ? null : mean(fs.map((f) => f.wavelength_um ?? 0)),
        flux_ujy: null,
        flux_err_ujy: null,
        target_px: [mean(fs.map((f) => f.target_px[0])), mean(fs.map((f) => f.target_px[1]))] as [number, number],
        png: `/api/sequences/${seq.id}/stack.png?band=${fs[0].band}&mjd_min=${Math.min(...mjds)}&mjd_max=${Math.max(...mjds)}`,
      }
    })
    .sort((a, b) => a.mjd - b.mjd)
}

/** Frames passing the band + flag filters; deep stacks in deep mode. */
const filterFrames = (seq: Sequence | null, fb: Flipbook) =>
  !seq
    ? []
    : fb.deep
      ? deepFrames(seq, fb.bands)
      : seq.frames.filter((f) => fb.bands.includes(f.band) && !(fb.hideFlagged && f.flagged))

type Shown = { png: string; label: string }
/** Blink pair of one band: earliest vs latest deep stack (WISE 2010–2011 vs 2022 onward, SPHEREx first vs last survey
 * epoch), plus a difference image of the first and last single frame of those windows (diff.png takes frames). */
function blinkPair(seq: Sequence, band: string): { a: Shown; b: Shown; diff: Shown } | null {
  const fs = seq.frames.filter((f) => f.band === band && !f.flagged).sort((x, y) => x.mjd - y.mjd)
  if (!fs.length) return null
  const yr = (f: Frame) => mjdToYear(f.mjd)
  const [first, last] = [fs[0], fs[fs.length - 1]]
  const [early, late] =
    first.survey === 'wise'
      ? [fs.filter((f) => yr(f) < 2012), fs.filter((f) => yr(f) >= 2022)]
      : [fs.filter((f) => f.epoch_index === first.epoch_index), fs.filter((f) => f.epoch_index === last.epoch_index)]
  if (!early.length || !late.length || early[0] === late[0]) return null
  const stack = (w: Frame[]): Shown => {
    const [y0, y1] = [w[0], w[w.length - 1]].map((f) => f.date.slice(0, 4))
    return {
      png: `/api/sequences/${seq.id}/stack.png?band=${band}&mjd_min=${w[0].mjd}&mjd_max=${w[w.length - 1].mjd}`,
      label: `${band} deep stack ${y0 === y1 ? y0 : `${y0}–${y1}`}`,
    }
  }
  const [f0, f1] = [early[0], late[late.length - 1]]
  return {
    a: stack(early),
    b: stack(late),
    diff: {
      png: `/api/sequences/${seq.id}/diff.png?a=${encodeURIComponent(f0.id)}&b=${encodeURIComponent(f1.id)}`,
      label: `Difference ${f1.date.slice(0, 10)} − ${f0.date.slice(0, 10)} ${band} (red = new, blue = old)`,
    },
  }
}

type Props = {
  seq: Sequence | null
  fb: Flipbook
  set: (patch: Partial<Flipbook>) => void
  aladin: Aladin | null
  /** offer Blink (earliest vs latest deep stack, optional difference image) */
  blink?: boolean
  /** band preset buttons shown instead of the per-band chips */
  presets?: { label: string; bands: string[]; title?: string }[]
  /** crop the viewer to a size×size px window around (x, y) (grid px, PNG y-down, epoch 2018.0) and mark a source
   * moving vx, vy px/yr instead of the target circle */
  focus?: { x: number; y: number; size: number; vx: number; vy: number }
  /** labelled circles for the frame on screen, drawn instead of the target circle */
  marks?: (f: Frame) => Mark[]
  /** viewer edge in CSS px (default 360) */
  viewerPx?: number
  /** draggable probe point with its apertures; right-click on the image places it there */
  probe?: ProbeCtl
}

export default function Player({ seq, fb, set, aladin, blink: canBlink, presets, focus, marks, viewerPx = 360, probe }: Props) {
  const playable = filterFrames(seq, fb)
  const idx = Math.max(0, playable.findIndex((f) => f.id === fb.frameId))
  const cur: Frame | undefined = playable[idx]
  const [blink, setBlink] = useState<{ diff: boolean; phase: 0 | 1 } | null>(null)
  const pair = canBlink && seq ? blinkPair(seq, cur?.band ?? fb.bands[0]) : null
  const override = blink && pair ? (blink.diff ? pair.diff : blink.phase ? pair.b : pair.a) : null

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

  // blink at ~1 Hz; playing or stepping to another frame ends it
  const blinking = !!blink && !blink.diff
  useEffect(() => {
    if (!blinking) return
    const t = setInterval(() => setBlink((b) => b && { ...b, phase: b.phase ? 0 : 1 }), 1000)
    return () => clearInterval(t)
  }, [blinking])
  useEffect(() => {
    if (fb.playing) setBlink(null)
  }, [fb.playing])
  useEffect(() => setBlink(null), [fb.frameId, fb.deep, seq?.id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === ' ' && !(e.target instanceof HTMLButtonElement)) {
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
  const wait = seq && waitText(seq.queue_position, seq.eta_s)
  // visible part of the grid: [x0, y0, w, h] in grid px
  const view = !seq
    ? [0, 0, 1, 1]
    : focus
      ? [Math.min(Math.max(focus.x - focus.size / 2, 0), seq.grid.width - focus.size), Math.min(Math.max(focus.y - focus.size / 2, 0), seq.grid.height - focus.size), focus.size, focus.size]
      : [0, 0, seq.grid.width, seq.grid.height]
  return (
    <div className="space-y-2 p-2 text-xs">
      {seq?.status === 'error' && <p className="text-red-400">{seq.error}</p>}
      {busy && (
        <div>
          <div className="mb-1 text-slate-400">
            {seq.status === 'querying' ? 'Querying IRSA archive…' : `Fetching frames ${seq.done}/${seq.total}`}
            {wait && <span className="ml-2 text-slate-300">· {wait}</span>}
          </div>
          <div className="h-1.5 rounded bg-slate-700">
            <div className="h-1.5 rounded bg-sky-500" style={{ width: `${seq.total ? (100 * seq.done) / seq.total : 3}%` }} />
          </div>
        </div>
      )}
      {/* overflow-hidden: probe annuli and focus crops reach far past the picture */}
      {/* phones: full width, square */}
      <div className="relative mx-auto overflow-hidden bg-black max-md:aspect-square max-md:h-auto! max-md:w-full!" style={{ width: viewerPx, height: viewerPx }}>
        {shownPng && seq ? (
          <svg
            role={probe ? 'group' : 'img'}
            aria-label={override?.label ?? `Frame ${cur?.date}`}
            viewBox={view.join(' ')}
            className="h-full w-full"
            // Chrome ignores touch-action on SVG children: without this a touch drag of the probe turns into a page scroll.
            // Only while a probe point exists, so on phones the picture still scrolls the page otherwise (the corner dock
            // has its own touch-action).
            style={probe?.point ? { touchAction: 'none' } : undefined}
            onContextMenu={
              probe &&
              ((e) => {
                e.preventDefault()
                const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(e.currentTarget.getScreenCTM()!.inverse())
                probe.place({ ...pxToWorld(seq.grid.wcs, seq.grid.height, pt.x - 0.5, pt.y - 0.5), pmra_masyr: 0, pmdec_masyr: 0 })
                probe.setMenu({ x: e.clientX, y: e.clientY })
              })
            }
          >
            <image href={shownPng} width={seq.grid.width} height={seq.grid.height} preserveAspectRatio="none" style={{ imageRendering: 'pixelated' }} />
            {focus ? (
              <>
                <line
                  x1={focus.x + 0.5 - 8 * focus.vx} y1={focus.y + 0.5 - 8 * focus.vy} x2={focus.x + 0.5 + 8 * focus.vx} y2={focus.y + 0.5 + 8 * focus.vy}
                  stroke="#38bdf8" strokeDasharray="4 4" strokeWidth={1} vectorEffect="non-scaling-stroke"
                />
                {cur && (
                  <circle
                    cx={focus.x + 0.5 + focus.vx * (mjdToYear(cur.mjd) - 2018)} cy={focus.y + 0.5 + focus.vy * (mjdToYear(cur.mjd) - 2018)}
                    r={APERTURE[cur.survey].r / PIX_ARCSEC} fill="none" stroke="#f472b6" strokeWidth={2} vectorEffect="non-scaling-stroke"
                  />
                )}
              </>
            ) : marks ? (
              !override && cur && <Marks marks={marks(cur)} width={seq.grid.width} />
            ) : (
              // the target's real photometry aperture
              !override && cur && (
                <circle cx={cur.target_px[0] + 0.5} cy={cur.target_px[1] + 0.5} r={APERTURE[cur.survey].r / PIX_ARCSEC} fill="none" stroke="#f472b6" strokeWidth={2} vectorEffect="non-scaling-stroke" />
              )
            )}
            {probe?.point && <ProbeMarker probe={probe} point={probe.point} seq={seq} frame={cur} unit={view[2] / viewerPx} />}
          </svg>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-500">{seq ? 'No frames match the filters' : 'No sequence'}</div>
        )}
        {probe && !probe.point && shownPng && seq && <ProbeDock probe={probe} seq={seq} />}
      </div>
      {probe && shownPng && !localStorage.getItem(PROBE_USED_KEY) && (
        <p className="text-cyan-300/80">
          Tip: drag the cyan crosshair from the corner onto any source<span className="max-md:hidden"> (or right-click it)</span> to measure it.
        </p>
      )}
      <div className="flex min-h-5 items-center gap-2 max-md:flex-wrap max-md:gap-x-1.5 max-md:whitespace-nowrap">
        {override ? (
          <span className="max-md:whitespace-normal">{override.label}</span>
        ) : (
          cur && (
            <>
              <span>{cur.kind === 'exposure' ? cur.date.slice(0, 16).replace('T', ' ') : cur.date.slice(0, 10)}</span>·<span>{cur.survey === 'wise' ? 'WISE' : 'SPHEREx'}</span>·<span>{cur.band}</span>·
              <span>{cur.wavelength_um?.toFixed(2)} µm</span>
              {(cur.flagged || !!cur.flag_names.length) && (
                <span className="truncate rounded bg-amber-700 px-1" title={cur.flag_names.length ? `Artifact flags at the target: ${cur.flag_names.join(', ')}` : 'Bad-pixel flags at the target'}>
                  {cur.flag_names.length ? cur.flag_names.join(' ') : 'flagged'}
                </span>
              )}
            </>
          )
        )}
        <span className="ml-auto text-slate-500">{playable.length ? `${idx + 1}/${playable.length}` : ''}</span>
      </div>
      <div className="flex items-center gap-1 max-md:flex-wrap">
        <button className="flex h-6 items-center rounded bg-slate-700 px-2 max-md:h-11 max-md:w-11 max-md:justify-center" aria-label="Previous frame" onClick={() => { set({ playing: false }); step(-1) }}><Icon d={ICON.prev} /></button>
        <button className="flex h-6 w-16 items-center justify-center gap-1 rounded bg-sky-700 px-2 max-md:h-11 max-md:w-24" onClick={() => set({ playing: !fb.playing })}>
          <Icon d={fb.playing ? ICON.pause : ICON.play} />
          {fb.playing ? 'Pause' : 'Play'}
        </button>
        <button className="flex h-6 items-center rounded bg-slate-700 px-2 max-md:h-11 max-md:w-11 max-md:justify-center" aria-label="Next frame" onClick={() => { set({ playing: false }); step(1) }}><Icon d={ICON.next} /></button>
        <input
          aria-label="Scrub"
          type="range"
          // phones: a row of its own under the buttons
          className="flex-1 max-md:order-last max-md:h-11 max-md:basis-full"
          min={0}
          max={Math.max(0, playable.length - 1)}
          value={idx}
          onChange={(e) => set({ playing: false, frameId: playable[Number(e.target.value)]?.id ?? null })}
        />
        <select aria-label="Frames per second" className="rounded bg-slate-800 px-1 py-1 max-md:ml-auto max-md:h-11 max-md:px-2" value={fb.fps} onChange={(e) => set({ fps: Number(e.target.value) })}>
          {[0.5, 1, 2, 4].map((f) => <option key={f} value={f}>{f} fps</option>)}
        </select>
      </div>
      <div role="group" aria-label="Bands" className="flex flex-wrap gap-1">
        {presets
          ? presets.map((p) => {
              const on = p.bands.length === fb.bands.length && p.bands.every((b) => fb.bands.includes(b))
              return (
                <button
                  key={p.label}
                  aria-pressed={on}
                  title={p.title}
                  className={`rounded px-2 py-0.5 max-md:min-h-11 max-md:px-3 ${on ? 'bg-sky-700' : 'bg-slate-800 text-slate-400'}`}
                  onClick={() => set({ bands: p.bands })}
                >
                  {p.label}
                </button>
              )
            })
          : ALL_BANDS.map((b) => {
              const on = fb.bands.includes(b)
              return (
                <button
                  key={b}
                  aria-pressed={on}
                  title={`${b.startsWith('W') ? 'WISE' : 'SPHEREx detector'} ${b}: ${BAND_UM[b]} µm`}
                  className={`rounded px-2 py-0.5 max-md:min-h-11 ${on ? 'bg-sky-700' : 'bg-slate-800 text-slate-400'}`}
                  onClick={() => set({ bands: on ? fb.bands.filter((x) => x !== b) : [...fb.bands, b] })}
                >
                  {b} <span className="text-[10px] opacity-70">{BAND_UM[b]} µm</span>
                </button>
              )
            })}
      </div>
      {/* phones have no hover: the chosen preset's wavelengths as text */}
      {presets && <p className="text-slate-400 md:hidden">{presets.find((p) => p.bands.length === fb.bands.length && p.bands.every((b) => fb.bands.includes(b)))?.title}</p>}
      <p className="text-slate-400 md:hidden">
        Flagged frames have artifacts (ghosts, afterimages, cosmic rays) at the target. Deep stacks add up 2 years of WISE or one SPHEREx survey to show
        fainter sources.
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 whitespace-nowrap">
        <label className="flex items-center gap-1 max-md:min-h-11" title="Leave out frames with artifact flags (ghosts, latents, cosmic rays) at the target">
          <input type="checkbox" checked={fb.hideFlagged} onChange={(e) => set({ hideFlagged: e.target.checked })} /> Hide flagged
          {fb.hideFlagged && seq && <span className="text-slate-500">({seq.frames.filter((f) => f.flagged && fb.bands.includes(f.band)).length})</span>}
        </label>
        {/* no sky map in Learn and Discover */}
        {aladin && (
          <label className="flex items-center gap-1 max-md:min-h-11">
            <input type="checkbox" checked={fb.showOnSky} onChange={(e) => set({ showOnSky: e.target.checked })} /> Show on sky
          </label>
        )}
        <label className="flex items-center gap-1 max-md:min-h-11" title="Co-add frames per band: WISE in 2-year windows, SPHEREx per survey epoch. Shows sources too faint for single frames.">
          <input type="checkbox" checked={fb.deep} onChange={(e) => set({ deep: e.target.checked, frameId: null })} /> Deep stacks
        </label>
      </div>
      {canBlink && (
        <div className="flex items-center gap-2">
          <button
            aria-pressed={!!blink}
            className={`rounded px-2 py-1 max-md:min-h-11 max-md:px-3 ${blink ? 'bg-amber-700' : 'bg-slate-700'} disabled:opacity-50`}
            disabled={!pair}
            title={pair ? `Alternate ${pair.a.label} and ${pair.b.label}` : 'Needs early and late frames of this band'}
            onClick={() => {
              set({ playing: false })
              setBlink(blink ? null : { diff: false, phase: 0 })
            }}
          >
            {blink ? 'Stop blink' : 'Blink'}
          </button>
          {blink && (
            <label className="flex items-center gap-1 max-md:min-h-11">
              <input type="checkbox" checked={blink.diff} onChange={(e) => setBlink({ diff: e.target.checked, phase: 0 })} /> show difference
            </label>
          )}
          {!blink && <span className="text-slate-500">earliest vs latest deep stack</span>}
        </div>
      )}
    </div>
  )
}

/** Labelled circles in grid-pixel SVG coordinates; sizes scale with the grid so they read the same at any field of view. */
export function Marks({ marks, width }: { marks: Mark[]; width: number }) {
  const r = Math.max(5, width / 40)
  const font = width / 26
  return (
    <>
      {marks.map((m, i) => {
        // keep labels inside the picture: anchor towards the centre near the edges; every other label goes below its circle
        // (and any label near the top edge) so neighbours at the same height do not overlap
        const anchor = m.x > 0.65 * width ? 'end' : m.x < 0.35 * width ? 'start' : 'middle'
        const tx = m.x + 0.5 + (anchor === 'end' ? r : anchor === 'start' ? -r : 0)
        const below = i % 2 === 1 || m.y - r * 1.3 < font
        const ty = below ? m.y + r * 1.3 + font : m.y + 0.5 - r * 1.3
        return (
          <g key={i}>
            <circle
              cx={m.x + 0.5} cy={m.y + 0.5} r={m.small ? r / 4 : r} fill="none" stroke="#f472b6" strokeWidth={m.small ? 1 : 2}
              strokeDasharray={m.faint ? '4 3' : undefined} opacity={m.faint ? 0.6 : 1} vectorEffect="non-scaling-stroke"
            />
            {m.label && (
              <text x={tx} y={ty} fontSize={font} textAnchor={anchor} fill="#fbcfe8" stroke="#000" strokeWidth={width / 120} paintOrder="stroke" opacity={m.faint ? 0.7 : 1}>
                {m.label}
              </text>
            )}
          </g>
        )
      })}
    </>
  )
}
