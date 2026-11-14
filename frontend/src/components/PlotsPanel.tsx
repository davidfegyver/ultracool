import Plotly from 'plotly.js-dist-min'
import { useEffect, useRef, useState } from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'
import { getCatalogLightcurve, getSpectrum, type CatalogLightcurve, type Sequence, type Spectrum } from '../api'
import { mjdToIso } from '../sky'
import { ALL_BANDS } from './Player'

export const Plot = createPlotlyComponent(Plotly)

// approximate molecular absorption bands in ultracool-dwarf spectra (µm)
const MOLECULES: [string, number, number][] = [
  ['H₂O', 1.1, 1.2], ['H₂O', 1.33, 1.5], ['H₂O', 1.75, 2.05], ['H₂O', 2.5, 3.0],
  ['CH₄', 1.6, 1.8], ['CH₄', 2.15, 2.5], ['CH₄', 3.2, 3.5],
  ['CO', 2.29, 2.4], ['CO', 4.5, 4.9], ['CO₂', 4.2, 4.35], ['NH₃', 2.9, 3.1],
]
const COLORS = ['#f87171', '#fb923c', '#a78bfa', '#818cf8', '#38bdf8', '#2dd4bf', '#4ade80', '#facc15']
export const DARK = {
  paper_bgcolor: '#0f172a',
  plot_bgcolor: '#0f172a',
  font: { color: '#cbd5e1', size: 11 },
  margin: { l: 60, r: 10, t: 10, b: 40 },
  legend: { orientation: 'h' as const, y: 1.12 },
}
const SPECTRUM_REFRESH_MS = 10_000

type Props = {
  seq: Sequence | null
  /** candidate periods in days, most likely first: enable "Fold at" (x = phase) */
  periods?: number[]
  /** only plot these bands in the light curve (default: all) */
  bands?: string[]
}

export default function PlotsPanel({ seq, periods = [], bands = ALL_BANDS }: Props) {
  const [tab, setTab] = useState<'lc' | 'spec'>('lc')
  // linear by default: faint targets have zero or negative fluxes, which a log axis silently drops
  const [logY, setLogY] = useState(false)
  const [foldAt, setFoldAt] = useState<number | null>(null)
  const [showCatalog, setShowCatalog] = useState(true)
  const [spec, setSpec] = useState<Spectrum | null>(null)
  const [catalog, setCatalog] = useState<CatalogLightcurve | null>(null)
  const last = useRef({ id: '', n: -1, t: 0 })

  // refetch when new frames arrive, at most every 10 s (and always once the job settles)
  const n = seq?.frames.length ?? 0
  const settled = seq?.status === 'done' || seq?.status === 'error'
  useEffect(() => {
    if (!seq) return setSpec(null)
    const l = last.current
    if (l.id === seq.id && (l.n === n || (!settled && Date.now() - l.t < SPECTRUM_REFRESH_MS))) return
    last.current = { id: seq.id, n, t: Date.now() }
    getSpectrum(seq.id).then(setSpec).catch(() => setSpec(null))
  }, [seq, n, settled])

  // catalog photometry: once at start, again when the job settles; a 404 (older backend) just means no fallback
  const sid = seq?.id
  useEffect(() => {
    if (!sid) return setCatalog(null)
    let stale = false
    getCatalogLightcurve(sid)
      .then((c) => !stale && setCatalog(c))
      .catch(() => !stale && setCatalog(null))
    return () => {
      stale = true
    }
  }, [sid, settled])

  type Pt = { mjd: number; flux: number; err: number; open: boolean; text: string }
  const own = (seq?.frames ?? []).filter((f) => f.flux_ujy !== null && bands.includes(f.band))
  const cat = (catalog?.points ?? []).filter((p) => p.flux_ujy !== null && bands.includes(p.band))
  const catalogOnly = !own.length && cat.length > 0
  const useCatalog = cat.length > 0 && (catalogOnly || showCatalog)
  const folded = foldAt !== null
  const mjd0 = Math.min(...own.map((f) => f.mjd), ...cat.map((p) => p.mjd))
  const trace = (name: string, color: string, symbol: string, pts: Pt[]) => {
    // folded: phase 0-2 (each point twice) so a cycle that wraps at phase 1 still reads as one curve
    const xs = folded ? [...pts, ...pts].map((p, i) => (((p.mjd - mjd0) / foldAt) % 1) + (i < pts.length ? 0 : 1)) : pts.map((p) => mjdToIso(p.mjd))
    const twice = <T,>(a: T[]) => (folded ? [...a, ...a] : a)
    return {
      type: 'scatter' as const,
      mode: 'markers' as const,
      name,
      x: xs,
      y: twice(pts.map((p) => p.flux)),
      error_y: { type: 'data' as const, array: twice(pts.map((p) => p.err)), thickness: 1, width: 0 },
      marker: { color, symbol: twice(pts.map((p) => (p.open ? `${symbol}-open` : symbol))), size: 6 },
      text: twice(pts.map((p) => p.text)),
    }
  }
  const lcTraces = [
    ...ALL_BANDS.map((b, i) =>
      trace(b, COLORS[i], 'circle', own.filter((f) => f.band === b).map((f) => ({
        mjd: f.mjd, flux: f.flux_ujy!, err: f.flux_err_ujy ?? 0, open: f.flagged, text: `${f.wavelength_um?.toFixed(2)} µm${f.flagged ? ' (flagged)' : ''}`,
      }))),
    ),
    ...(useCatalog
      ? ALL_BANDS.map((b, i) =>
          trace(`${b} WISE catalog`, COLORS[i], 'diamond', cat.filter((p) => p.band === b).map((p) => ({
            mjd: p.mjd, flux: p.flux_ujy!, err: p.flux_err_ujy ?? 0, open: false, text: `WISE catalog, ${p.n} exposures${p.mag !== null ? `, ${p.mag.toFixed(2)} mag` : ''}`,
          }))),
        )
      : []),
  ].filter((t) => t.x.length)

  const header = spec?.best
    ? `Best match: ${spec.best.label} (p=${spec.best.prob.toFixed(2)}, χ²ᵣ=${spec.best.chi2_red.toFixed(2)}, ${spec.best.n_bins} bins)` +
      (spec.verdict === 'match' ? '' : ` · ${spec.verdict}`)
    : (spec?.verdict ?? '')

  return (
    <div className="flex h-full flex-col text-xs">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-slate-700 px-2 py-1 whitespace-nowrap">
        {(['lc', 'spec'] as const).map((t) => (
          <button key={t} className={`rounded px-2 py-0.5 ${tab === t ? 'bg-sky-700' : 'bg-slate-800'}`} onClick={() => setTab(t)}>
            {t === 'lc' ? 'Light curve' : 'Spectrum'}
          </button>
        ))}
        {tab === 'lc' && (
          <>
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={logY} onChange={(e) => setLogY(e.target.checked)} /> log y
            </label>
            {periods.length > 0 && (
              <label className="flex items-center gap-1" title="Plot brightness against the phase of the cycle instead of the date. WISE's 6-month visits cannot tell some periods apart: try each.">
                Fold at
                <select className="rounded bg-slate-800 px-1" value={foldAt ?? ''} onChange={(e) => setFoldAt(e.target.value === '' ? null : Number(e.target.value))}>
                  <option value="">off (time)</option>
                  {periods.map((p) => (
                    <option key={p} value={p}>
                      {p.toFixed(1)} d
                    </option>
                  ))}
                </select>
              </label>
            )}
            {catalogOnly ? (
              <span className="text-amber-300" title={`Too bright for our own measurements; points from ${catalog?.source}`}>
                WISE catalog photometry
              </span>
            ) : (
              cat.length > 0 && (
                <label className="flex items-center gap-1" title={catalog?.source}>
                  <input type="checkbox" checked={showCatalog} onChange={(e) => setShowCatalog(e.target.checked)} /> WISE catalog photometry
                </label>
              )
            )}
          </>
        )}
        {tab === 'spec' && <span className="text-slate-300">{header}</span>}
        {tab === 'spec' && spec && spec.ranking.length > 1 && (
          <span className="text-slate-500">
            next: {spec.ranking.slice(1, 4).map((r) => `${r.label} (${r.prob.toFixed(2)})`).join(', ')}
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1">
        {tab === 'lc' ? (
          <Plot
            className="h-full w-full"
            useResizeHandler
            data={lcTraces}
            layout={{
              ...DARK,
              xaxis: { title: { text: folded ? `Phase (period ${foldAt.toFixed(1)} d)` : 'Date' } },
              yaxis: { title: { text: 'Flux (µJy, aperture-corrected)' }, type: logY ? 'log' : 'linear' },
              annotations:
                settled && !lcTraces.length
                  ? [{ x: 0.5, y: 0.5, xref: 'paper', yref: 'paper', text: 'No brightness measurements for this object', showarrow: false, font: { size: 13, color: '#94a3b8' } }]
                  : [],
            }}
            config={{ displaylogo: false, responsive: true }}
          />
        ) : (
          <Plot
            className="h-full w-full"
            useResizeHandler
            data={[
              {
                type: 'scatter',
                mode: 'markers',
                name: 'SPHEREx (binned)',
                x: spec?.binned.map((b) => b.wavelength_um) ?? [],
                y: spec?.binned.map((b) => b.flambda) ?? [],
                error_y: { type: 'data', array: spec?.binned.map((b) => b.err) ?? [], thickness: 1, width: 0 },
                marker: { color: '#38bdf8', size: 6 },
              },
              ...(spec?.template_curve
                ? [{
                    type: 'scatter',
                    mode: 'lines',
                    name: `Template ${spec.template_curve.label}`,
                    x: spec.template_curve.wavelength_um,
                    y: spec.template_curve.flambda,
                    line: { color: '#f472b6' },
                  }]
                : []),
            ]}
            layout={{
              ...DARK,
              xaxis: { title: { text: 'Wavelength (µm)' }, range: [0.7, 5.1] },
              yaxis: { title: { text: 'F_λ (arbitrary)' } },
              shapes: MOLECULES.map(([, a, b], i) => ({
                type: 'rect', xref: 'x', yref: 'paper', x0: a, x1: b, y0: 0, y1: 1,
                fillcolor: i % 2 ? '#64748b' : '#475569', opacity: 0.18, line: { width: 0 }, layer: 'below',
              })),
              annotations: [
                ...MOLECULES.map(([m, a, b], i) => ({
                  x: (a + b) / 2, y: i % 2 ? 0.98 : 0.92, xref: 'x', yref: 'paper', text: m, showarrow: false, font: { size: 10, color: '#94a3b8' },
                })),
                { x: 1, y: 0.02, xref: 'paper', yref: 'paper', xanchor: 'right', text: 'molecule bands approximate', showarrow: false, font: { size: 9, color: '#64748b' } },
              ],
            }}
            config={{ displaylogo: false, responsive: true }}
          />
        )}
      </div>
    </div>
  )
}
