import { useEffect, useRef, useState } from 'react'
import type { Frame, Sequence } from '../api'
import { downloadCsv } from '../csv'
import type { ProbeCtl, ProbePoint } from '../hooks'
import { propagate, pxToWorld, worldToPx } from '../sky'
import FoundPanel from './FoundPanel'
import Pending from './Pending'
import PlotsPanel from './PlotsPanel'
import { PhotometryTables } from './ResearchPanel'

const PIX_ARCSEC = 2.75
// photometry aperture radii of the backend (SPHEREx 2 native px, WISE 3 grid px) and their sky annuli
const APERTURE: Record<Frame['survey'], { r: number; sky: [number, number] }> = {
  spherex: { r: 12.3, sky: [24.6, 43] },
  wise: { r: 8.25, sky: [50, 70] },
}
const CYAN = '#22d3ee'
const MJD_2018 = 58119 // grid epoch, used when no frame is on screen

/** Probe point drawn inside the flipbook SVG (grid px): cyan crosshair, the frame's photometry aperture (solid) and sky
 * annulus (dashed). Drag (mouse/touch) or arrow keys (Shift = 5 px) move it; release, a click or Enter opens the action
 * menu. Moving never measures. Without a point yet, a faint "drag me" marker sits at `ghostAt`. */
export function ProbeMarker({ probe, seq, frame, ghostAt, unit }: {
  probe: ProbeCtl
  seq: Sequence
  frame: Frame | undefined
  ghostAt: [number, number]
  /** grid px per CSS px, so the crosshair and hit area keep their on-screen size */
  unit: number
}) {
  const [drag, setDrag] = useState<{ at: [number, number]; moved: boolean } | null>(null)
  const [focused, setFocused] = useState(false)
  const { wcs, height } = seq.grid
  const p = probe.point
  const q = p && propagate(p.ra, p.dec, p.pmra_masyr, p.pmdec_masyr, 2000, frame?.mjd ?? MJD_2018)
  const at = q ? worldToPx(wcs, height, q.ra, q.dec) : ghostAt
  const [x, y] = drag?.at ?? at
  const ap = APERTURE[frame?.survey ?? 'wise']

  // a manual move picks a new spot, so any adopted proper motion is dropped (measuring may adopt a mover's again)
  const commit = ([px, py]: [number, number]) => probe.place({ ...pxToWorld(wcs, height, px, py), pmra_masyr: 0, pmdec_masyr: 0 })
  const toGrid = (e: React.PointerEvent<SVGGElement>): [number, number] => {
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(e.currentTarget.ownerSVGElement!.getScreenCTM()!.inverse())
    return [pt.x - 0.5, pt.y - 0.5]
  }
  const label = p
    ? `Probe at RA ${p.ra.toFixed(5)}, Dec ${p.dec.toFixed(5)}. Drag or use arrow keys to move; Enter for actions`
    : 'Probe: drag onto a source, or press Enter for actions'

  return (
    <g opacity={p || drag ? 1 : 0.55}>
      {/* apertures stay out of the focus/hit box, so neighbours inside them remain right-clickable */}
      <g pointerEvents="none">
        <circle cx={x + 0.5} cy={y + 0.5} r={ap.r / PIX_ARCSEC} fill="none" stroke={CYAN} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        {ap.sky.map((r) => (
          <circle key={r} cx={x + 0.5} cy={y + 0.5} r={r / PIX_ARCSEC} fill="none" stroke={CYAN} strokeWidth={1} strokeDasharray="3 3" opacity={0.7} vectorEffect="non-scaling-stroke" />
        ))}
      </g>
      <g
        role="button"
        tabIndex={0}
        aria-label={label}
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
          if (drag.moved || !p) commit(drag.at)
          setDrag(null)
          probe.setMenu({ x: e.clientX, y: e.clientY })
        }}
        onPointerCancel={() => setDrag(null)}
        onContextMenu={(e) => {
          e.preventDefault()
          e.stopPropagation()
          if (!p) commit(at)
          probe.setMenu({ x: e.clientX, y: e.clientY })
        }}
        onKeyDown={(e) => {
          const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key]
          if (d) {
            const s = e.shiftKey ? 5 : 1
            commit([at[0] + d[0] * s, at[1] + d[1] * s])
          } else if (e.key === 'Enter') {
            if (!p) commit(at)
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
        {!p && !drag && (
          <text x={x + 0.5} y={y + 0.5 - 13 * unit} fontSize={11 * unit} textAnchor="middle" fill={CYAN} stroke="#000" strokeWidth={3 * unit} paintOrder="stroke">
            drag me
          </text>
        )}
      </g>
    </g>
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
    back.current?.focus()
  }
  useEffect(() => {
    if (!menu) return
    back.current = document.activeElement as HTMLElement | null
    ref.current?.querySelector('button')?.focus()
    const away = (e: PointerEvent) => !ref.current?.contains(e.target as Node) && setMenu(null)
    document.addEventListener('pointerdown', away)
    return () => document.removeEventListener('pointerdown', away)
  }, [menu, setMenu])
  if (!menu || !point) return null

  const item = 'block w-full rounded px-2 py-1 text-left hover:bg-slate-700 focus:bg-slate-700 focus:outline-none disabled:text-slate-500'
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
      <button role="menuitem" className={item} disabled={!probe.sid} onClick={() => probe.measure('preview')}>
        Measure this source
      </button>
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
 * (Research), and light-curve/spectrum plots. */
export function ProbePanel({ probe, research }: { probe: ProbeCtl; research: boolean }) {
  const { data: d, point, busy, progress, error } = probe
  const box = useRef<HTMLDivElement>(null)
  // a measurement started from the menu: bring its progress and result into view
  useEffect(() => {
    if (busy) box.current?.scrollIntoView({ block: 'start' })
  }, [busy])
  if (!point && !d)
    return <p className="p-2 text-xs text-slate-500">Drag the cyan probe in the flipbook, or right-click the sky map, to measure any source in the field.</p>
  const moved = d && point !== probe.measuredAt
  const full = d?.mode === 'full'
  const btn = 'rounded px-2 py-1 enabled:hover:bg-sky-600 disabled:opacity-50'
  return (
    <div ref={box} className="space-y-2 p-2 text-xs">
      {d && (
        <table className="w-full">
          <tbody>
            {[
              ['Measured', full ? 'full (native pixels)' : 'quick preview (resampled images)'],
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
      {moved && <p className="text-amber-300">The probe has moved since this measurement.</p>}
      <div className="flex flex-wrap items-center gap-2">
        {(!d || moved) && (
          <button className={`${btn} bg-sky-700`} disabled={busy || !probe.sid} onClick={() => probe.measure('preview')}>
            Measure this source
          </button>
        )}
        {d && !full && !moved && (
          <button className={`${btn} bg-sky-700`} disabled={busy} onClick={() => probe.measure('full')} title="Re-measures the native SPHEREx pixels and WISE co-adds exactly like the target">
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
      {busy && !progress && <Pending note="Measuring…" busy />}
      {progress && (
        <div role="status" aria-label="Full measurement progress">
          <div className="mb-1 text-slate-400">Full measurement: {progress.total ? `${progress.done}/${progress.total} frames` : 'queued…'}</div>
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
      {d && (
        <div className="h-64 border border-slate-700">
          <PlotsPanel seq={null} probe={{ frames: d.frames, spectrum: d.spectrum }} />
        </div>
      )}
    </div>
  )
}
