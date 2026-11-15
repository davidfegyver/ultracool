import { useEffect, useRef, useState } from 'react'
import { waitText, type Frame, type Sequence } from '../api'
import { downloadCsv } from '../csv'
import type { ProbeCtl, ProbePoint } from '../hooks'
import { APERTURE, MJD_2018, PIX_ARCSEC, propagate, pxToWorld, worldToPx } from '../sky'
import FoundPanel from './FoundPanel'
import Pending from './Pending'
import PlotsPanel from './PlotsPanel'
import { PhotometryTables } from './ResearchPanel'

const CYAN = '#22d3ee'
const OUTSIDE_HINT = 'Too close to the edge to measure. Drag the probe further in, or choose Centre field here.'

/** Probe point drawn inside the flipbook SVG (grid px): cyan crosshair, the frame's photometry aperture (solid) and sky
 * annulus (dashed). Drag (mouse/touch) or arrow keys (Shift = 5 px) move it; release, a click or Enter opens the action
 * menu. Moving never measures. Only drawn once a point exists (see ProbeDock). */
export function ProbeMarker({ probe, point: p, seq, frame, unit }: {
  probe: ProbeCtl
  point: ProbePoint
  seq: Sequence
  frame: Frame | undefined
  /** grid px per CSS px, so the crosshair and hit area keep their on-screen size */
  unit: number
}) {
  const [drag, setDrag] = useState<{ at: [number, number]; moved: boolean } | null>(null)
  const [focused, setFocused] = useState(false)
  const { wcs, height } = seq.grid
  const q = propagate(p.ra, p.dec, p.pmra_masyr, p.pmdec_masyr, 2000, frame?.mjd ?? MJD_2018)
  const at = worldToPx(wcs, height, q.ra, q.dec)
  const [x, y] = drag?.at ?? at
  const ap = APERTURE[frame?.survey ?? 'wise']

  // a manual move picks a new spot, so any adopted proper motion is dropped (measuring may adopt a mover's again)
  const commit = ([px, py]: [number, number]) => probe.place({ ...pxToWorld(wcs, height, px, py), pmra_masyr: 0, pmdec_masyr: 0 })
  const toGrid = (e: React.PointerEvent<SVGGElement>): [number, number] => {
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(e.currentTarget.ownerSVGElement!.getScreenCTM()!.inverse())
    return [pt.x - 0.5, pt.y - 0.5]
  }

  return (
    <g>
      {/* apertures stay out of the focus/hit box, so neighbours inside them remain right-clickable */}
      <g pointerEvents="none">
        <circle cx={x + 0.5} cy={y + 0.5} r={ap.r / PIX_ARCSEC} fill="none" stroke={CYAN} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        {ap.sky.map((r) => (
          <circle key={r} cx={x + 0.5} cy={y + 0.5} r={r / PIX_ARCSEC} fill="none" stroke={CYAN} strokeWidth={1} strokeDasharray="3 3" opacity={0.7} vectorEffect="non-scaling-stroke" />
        ))}
      </g>
      <g
        data-probe-marker
        role="button"
        tabIndex={0}
        aria-label={`Probe at RA ${p.ra.toFixed(5)}, Dec ${p.dec.toFixed(5)}. Drag or use arrow keys to move; Enter for actions`}
        aria-haspopup="menu"
        className="cursor-move outline-none"
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onPointerDown={(e) => {
          if (e.button !== 0) return
          e.preventDefault()
          e.stopPropagation()
          e.currentTarget.setPointerCapture(e.pointerId)
          probe.setMenu(null)
          e.currentTarget.focus() // pointerdown's preventDefault skips the usual focus; arrow keys work right after a drag
          setDrag({ at, moved: false })
        }}
        onPointerMove={(e) => drag && setDrag({ at: toGrid(e), moved: true })}
        onPointerUp={(e) => {
          if (!drag) return
          if (drag.moved) commit(drag.at)
          setDrag(null)
          probe.setMenu({ x: e.clientX, y: e.clientY })
        }}
        onPointerCancel={() => setDrag(null)}
        onContextMenu={(e) => {
          e.preventDefault()
          e.stopPropagation()
          probe.setMenu({ x: e.clientX, y: e.clientY })
        }}
        onKeyDown={(e) => {
          const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key]
          if (d) {
            const s = e.shiftKey ? 5 : 1
            commit([at[0] + d[0] * s, at[1] + d[1] * s])
          } else if (e.key === 'Enter') {
            const r = e.currentTarget.getBoundingClientRect()
            probe.setMenu({ x: r.left + r.width / 2, y: r.top + r.height / 2 })
          } else return
          // keep the flipbook's arrow-key frame stepping and page scrolling out of it
          e.preventDefault()
          e.stopPropagation()
        }}
      >
        <circle cx={x + 0.5} cy={y + 0.5} r={14 * unit} fill="transparent" />
        {focused && <circle cx={x + 0.5} cy={y + 0.5} r={11 * unit} fill="none" stroke="#fde047" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />}
        {[[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => (
          <line
            key={`${dx}${dy}`}
            x1={x + 0.5 + dx * 3 * unit} y1={y + 0.5 + dy * 3 * unit} x2={x + 0.5 + dx * 11 * unit} y2={y + 0.5 + dy * 11 * unit}
            stroke={CYAN} strokeWidth={2} vectorEffect="non-scaling-stroke"
          />
        ))}
      </g>
    </g>
  )
}

/** Faint cyan crosshair docked in the viewer's top-left corner while there is no probe: drag it onto a source to start
 * one; a click or Enter puts it in the middle of the view. Either way the action menu opens; nothing is measured yet. */
export function ProbeDock({ probe, seq }: { probe: ProbeCtl; seq: Sequence }) {
  const [drag, setDrag] = useState<{ x0: number; y0: number; dx: number; dy: number } | null>(null)
  const placeAt = (dock: HTMLElement, cx: number, cy: number) => {
    const svg = dock.parentElement!.querySelector<SVGSVGElement>(':scope > svg')!
    const r = svg.getBoundingClientRect()
    if (cx < r.left || cx > r.right || cy < r.top || cy > r.bottom) return // dropped outside the picture
    const pt = new DOMPoint(cx, cy).matrixTransform(svg.getScreenCTM()!.inverse())
    probe.place({ ...pxToWorld(seq.grid.wcs, seq.grid.height, pt.x - 0.5, pt.y - 0.5), pmra_masyr: 0, pmdec_masyr: 0 })
    probe.setMenu({ x: cx, y: cy })
  }
  const centreOf = (el: HTMLElement) => {
    const r = el.parentElement!.querySelector(':scope > svg')!.getBoundingClientRect()
    return [r.left + r.width / 2, r.top + r.height / 2] as const
  }
  const label = 'Drag onto any source to measure it'
  return (
    <button
      aria-label={label}
      title={label}
      aria-haspopup="menu"
      className={`absolute top-1 left-1 z-10 flex h-7 w-7 items-center justify-center rounded-full max-md:h-11 max-md:w-11 max-md:opacity-90 ${drag ? 'cursor-grabbing' : 'cursor-grab bg-black/40 opacity-60 hover:opacity-100 focus-visible:opacity-100'}`}
      style={{ touchAction: 'none', transform: drag ? `translate(${drag.dx}px, ${drag.dy}px)` : undefined }}
      onPointerDown={(e) => {
        if (e.button !== 0) return
        e.preventDefault()
        e.currentTarget.setPointerCapture(e.pointerId)
        setDrag({ x0: e.clientX, y0: e.clientY, dx: 0, dy: 0 })
      }}
      onPointerMove={(e) => drag && setDrag({ ...drag, dx: e.clientX - drag.x0, dy: e.clientY - drag.y0 })}
      onPointerUp={(e) => {
        if (!drag) return
        setDrag(null)
        if (Math.hypot(drag.dx, drag.dy) < 4) return placeAt(e.currentTarget, ...centreOf(e.currentTarget))
        // where the crosshair is drawn, not where it was grabbed
        const b = e.currentTarget.getBoundingClientRect()
        placeAt(e.currentTarget, b.left + b.width / 2, b.top + b.height / 2)
      }}
      onPointerCancel={() => setDrag(null)}
      // keyboard activation (pointer clicks are handled on pointerup)
      onClick={(e) => e.detail === 0 && placeAt(e.currentTarget, ...centreOf(e.currentTarget))}
    >
      <svg viewBox="-12 -12 24 24" className="h-6 w-6" aria-hidden>
        <circle r={7} fill="none" stroke={CYAN} strokeWidth={1.5} />
        <path d="M0 -11v6M0 5v6M-11 0h6M5 0h6" stroke={CYAN} strokeWidth={2} />
      </svg>
    </button>
  )
}

/** Action menu next to the probe: measure it, recentre the field on it, or cancel. Arrow keys move between items,
 * Escape closes and returns focus. */
export function ProbeMenu({ probe, onCentre }: { probe: ProbeCtl; onCentre: (p: ProbePoint) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const { menu, point, setMenu } = probe
  const back = useRef<HTMLElement | null>(null)
  const close = () => {
    setMenu(null)
    // the dock that opened the menu is gone once a probe exists (and a mouse drag focuses nothing): go to the probe
    const b = back.current
    const to = b && b !== document.body && b.isConnected ? b : document.querySelector<SVGGElement>('[data-probe-marker]')
    to?.focus()
  }
  useEffect(() => {
    if (!menu) return
    back.current = document.activeElement as HTMLElement | null
    ref.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus()
    const away = (e: PointerEvent) => !ref.current?.contains(e.target as Node) && setMenu(null)
    document.addEventListener('pointerdown', away)
    return () => document.removeEventListener('pointerdown', away)
  }, [menu, setMenu])
  if (!menu || !point) return null

  const item = 'block w-full rounded px-2 py-1 text-left hover:bg-slate-700 focus:bg-slate-700 focus:outline-none disabled:text-slate-500 max-md:min-h-11'
  return (
    <div
      ref={ref}
      role="menu"
      aria-label="Probe actions"
      className="fixed z-50 w-56 rounded border border-cyan-700 bg-slate-900/95 p-1 text-xs shadow-xl"
      style={{ left: Math.min(menu.x + 12, innerWidth - 232), top: Math.min(menu.y + 12, innerHeight - 150) }}
      onKeyDown={(e) => {
        const items = [...ref.current!.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')]
        const i = items.indexOf(document.activeElement as HTMLButtonElement)
        if (e.key === 'Escape' || e.key === 'Tab') close()
        else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') items[(i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length]?.focus()
        else return
        e.preventDefault()
        e.stopPropagation()
      }}
    >
      <div className="px-2 py-1 font-mono text-cyan-300">
        {point.ra.toFixed(5)}, {point.dec.toFixed(5)}
        {(point.pmra_masyr !== 0 || point.pmdec_masyr !== 0) && <div className="text-slate-400">μ {(Math.hypot(point.pmra_masyr, point.pmdec_masyr) / 1000).toFixed(2)}″/yr</div>}
      </div>
      <button role="menuitem" className={item} disabled={!probe.sid || probe.outside} aria-describedby={probe.outside ? 'probe-outside-menu' : undefined} onClick={() => probe.measure('preview')}>
        Measure this source
      </button>
      {probe.outside && (
        <p id="probe-outside-menu" className="px-2 pb-1 text-amber-300">
          {OUTSIDE_HINT}
        </p>
      )}
      <button
        role="menuitem"
        className={item}
        onClick={() => {
          setMenu(null)
          onCentre(point)
        }}
      >
        Centre field here
      </button>
      <button role="menuitem" className={item} onClick={close}>
        Cancel
      </button>
    </div>
  )
}

/** Probe results: position, snapping and pm source, preview/full status, then badges + sentences (Explore) or tables
 * (Research), and light-curve/spectrum plots unless the page shows them elsewhere (`plots={false}`). */
export function ProbePanel({ probe, research, plots = true }: { probe: ProbeCtl; research: boolean; plots?: boolean }) {
  const { data: d, point, busy, progress, error } = probe
  const box = useRef<HTMLDivElement>(null)
  // a measurement started from the menu: bring its progress and result into view
  useEffect(() => {
    if (busy) box.current?.scrollIntoView({ block: 'start' })
  }, [busy])
  if (!point && !d)
    return (
      <p className="p-2 text-xs text-slate-500">
        To measure another source, drag the cyan crosshair from the flipbook's corner onto it<span className="max-md:hidden">, or right-click it</span>.
      </p>
    )
  const moved = d && point !== probe.measuredAt
  const full = d?.mode === 'full'
  const btn = 'rounded px-2 py-1 enabled:hover:bg-sky-600 disabled:opacity-50 max-md:min-h-11'
  return (
    <div ref={box} className="space-y-2 p-2 text-xs">
      {d && (
        <table className="w-full">
          <tbody>
            {[
              ['Measured', full ? 'full (native pixels)' : 'quick preview (from the resampled images)'],
              ['RA, Dec (2000)', `${d.position.ra.toFixed(5)}, ${d.position.dec.toFixed(5)}`],
              ['Snapped to peak', d.position.snapped ? `yes, ${d.position.snap_offset_arcsec.toFixed(1)}″ from the click` : 'no peak ≥3σ within 4″'],
              [
                'Proper motion',
                d.pm.source === 'none'
                  ? 'none assumed'
                  : `${d.pm.pmra_masyr.toFixed(0)}, ${d.pm.pmdec_masyr.toFixed(0)} mas/yr (${d.pm.source === 'mover' ? 'from a detected mover' : 'given'})`,
              ],
            ].map(([k, v]) => (
              <tr key={k} className="border-b border-slate-800">
                <th className="py-0.5 pr-2 text-left font-normal text-slate-400">{k}</th>
                <td className="text-right">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {moved && <p className="text-amber-300">You moved the probe after this measurement.</p>}
      <div className="flex flex-wrap items-center gap-2">
        {(!d || moved) && (
          <button className={`${btn} bg-sky-700`} disabled={busy || !probe.sid || probe.outside} aria-describedby={probe.outside ? 'probe-outside-panel' : undefined} onClick={() => probe.measure('preview')}>
            Measure this source
          </button>
        )}
        {d && !full && !moved && (
          <button className={`${btn} bg-sky-700`} disabled={busy} onClick={() => probe.measure('full')} title="Measures the original SPHEREx pixels and WISE stacks, the same way as the main target">
            Full measurement (~1-2 min)
          </button>
        )}
        {research && d && (
          <button
            className={`${btn} bg-slate-700`}
            onClick={() => downloadCsv(`ultracool_probe_${d.position.ra.toFixed(5)}_${d.position.dec.toFixed(5)}_${d.mode}.csv`, ['frame_id', 'survey', 'band', 'mjd', 'wavelength_um', 'flux_ujy', 'flux_err_ujy', 'flagged'], d.frames)}
          >
            ⤓ CSV
          </button>
        )}
      </div>
      {probe.outside && (
        <p id="probe-outside-panel" className="text-amber-300">
          {OUTSIDE_HINT}
        </p>
      )}
      {busy && !progress && <Pending note="Measuring…" busy />}
      {progress && (
        <div role="status" aria-label="Full measurement progress">
          <div className="mb-1 text-slate-400">
            Full measurement: {progress.total ? `${progress.done}/${progress.total} frames` : 'queued…'}
            {progress.queue_position ? ` · ${waitText(progress.queue_position)}` : ''}
          </div>
          <div className="h-1.5 rounded bg-slate-700">
            <div className="h-1.5 rounded bg-cyan-500" style={{ width: `${progress.total ? (100 * progress.done) / progress.total : 3}%` }} />
          </div>
        </div>
      )}
      {error && <p className="text-red-400">{error}</p>}
      {d &&
        (research ? (
          <>
            <ul className="space-y-0.5 text-slate-400">{d.plain.map((s) => <li key={s}>{s}</li>)}</ul>
            <PhotometryTables color={d.color} variability={d.variability} spectrum={d.spectrum} />
          </>
        ) : (
          <FoundPanel summary={d} note={null} busy={false} />
        ))}
      {d && plots && (
        <div className="h-64 border border-slate-700">
          <PlotsPanel seq={null} probe={{ frames: d.frames, spectrum: d.spectrum }} research={research} />
        </div>
      )}
    </div>
  )
}
