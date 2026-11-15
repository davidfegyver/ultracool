import Plotly from 'plotly.js-dist-min'
import { useEffect, useRef, useState } from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'
import { getCatalogLightcurve, getSpectrum, type CatalogLightcurve, type ProbeFrame, type Sequence, type Spectrum } from '../api'
import { useIsPhone } from '../hooks'
import { mjdToIso, mjdToYear } from '../sky'
import { ALL_BANDS } from './Player'

export const Plot = createPlotlyComponent(Plotly)

// approximate molecular absorption bands in ultracool-dwarf spectra (µm)
const MOLECULES: [string, number, number][] = [
  ['H₂O', 1.1, 1.2], ['H₂O', 1.33, 1.5], ['H₂O', 1.75, 2.05], ['H₂O', 2.5, 3.0],
  ['CH₄', 1.6, 1.8], ['CH₄', 2.15, 2.5], ['CH₄', 3.2, 3.5],
  // labels alternate between two heights by index: CO 2.29–2.4 at an even index so it does not overprint CH₄ 2.15–2.5
  ['CO', 4.5, 4.9], ['CO', 2.29, 2.4], ['CO₂', 4.2, 4.35], ['NH₃', 2.9, 3.1],
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
  /** plot a probe measurement instead of the sequence target (pass seq null): nothing is fetched */
  probe?: { frames: ProbeFrame[]; spectrum: Spectrum | null }
  /** Research mode: fit numbers and the per-frame "by date" spectrum; otherwise a plain-English header */
  research?: boolean
}

// /spectrum F_λ values are F_ν(µJy)/λ(µm)²; F_λ = c F_ν / λ² = 2.998e-18 W m⁻² µm⁻¹ per µJy/µm²
const TO_FLAMBDA = 2.998
const AXIS_NOTE = {
  lc: 'Brightness: aperture photometry, corrected for light outside the aperture',
  spec: 'F_λ: brightness at each wavelength, in 10⁻¹⁸ W m⁻² µm⁻¹',
}
const FOLD_NOTE = "Plot brightness against the phase of the cycle instead of the date. WISE's 6-month visits cannot tell some periods apart: try each."

/** "Looks like a T5 brown dwarf (good fit)" or the verdict as a sentence (Explore and Learn). */
function plainSpectrum(spec: Spectrum | null) {
  if (!spec) return ''
  const b = spec.best
  if (spec.verdict === 'match' && b) {
    const fit = b.chi2_red <= 2 ? 'good fit' : b.chi2_red <= 5 ? 'fair fit' : 'rough fit'
    return `Looks like ${/^[ML]/.test(b.label) ? 'an' : 'a'} ${b.label} ${b.label.startsWith('M') ? 'dwarf' : 'brown dwarf'} (${fit})`
  }
  if (spec.verdict === 'insufficient data') return 'Not enough SPHEREx measurements to tell its type'
  if (spec.verdict.startsWith('not consistent')) return 'Does not look like a brown dwarf'
  return spec.verdict.charAt(0).toUpperCase() + spec.verdict.slice(1)
}

export default function PlotsPanel({ seq, periods = [], bands = ALL_BANDS, probe, research = false }: Props) {
  const [tab, setTab] = useState<'lc' | 'spec'>('lc')
  // phones: no hover, so the ⓘ toggles its notes inline; no modebar and no drag-zoom (a drag scrolls the page)
  const phone = useIsPhone()
  const [notesOpen, setNotesOpen] = useState(false)
  const config = { displaylogo: false, responsive: true, ...(phone && { displayModeBar: false, scrollZoom: false }) }
  // legend anchored above the plot area, so Plotly grows the top margin for its rows instead of drawing over the points
  const phoneLayout = phone
    ? { dragmode: false as const, font: { ...DARK.font, size: 14 }, margin: { l: 56, r: 8, t: 8, b: 44 }, legend: { orientation: 'h' as const, x: 0, y: 1.02, yanchor: 'bottom' as const } }
    : {}
  // linear by default: faint targets have zero or negative fluxes, which a log axis silently drops
  const [logY, setLogY] = useState(false)
  const [foldAt, setFoldAt] = useState<number | null>(null)
  const [showCatalog, setShowCatalog] = useState(true)
  // SPHEREx points are each at a different wavelength: not a light curve unless asked for
  const [showSpherex, setShowSpherex] = useState(false)
  const [byDate, setByDate] = useState(false)
  const [fetched, setSpec] = useState<Spectrum | null>(null)
  const spec = probe ? probe.spectrum : fetched
  const [catalog, setCatalog] = useState<CatalogLightcurve | null>(null)
  const last = useRef({ id: '', n: -1, t: 0 })

  // refetch when new frames arrive, at most every 10 s (and always once the job settles)
  const n = seq?.frames.length ?? 0
  const settled = !!probe || seq?.status === 'done' || seq?.status === 'error'
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
  const all = (probe?.frames ?? seq?.frames ?? []).filter((f) => f.flux_ujy !== null && bands.includes(f.band))
  const sx = all.filter((f) => f.survey === 'spherex')
  const own = showSpherex ? all : all.filter((f) => f.survey === 'wise')
  // single SPHEREx frames as F_λ ∝ flux/λ², the units of the binned spectrum
  const sxSpec = sx.filter((f) => !f.flagged && f.wavelength_um)
  const lam2 = (f: (typeof sx)[number]) => f.wavelength_um! ** 2
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

  const header = !research
    ? plainSpectrum(spec)
    : spec?.best
      ? `Best match: ${spec.best.label}` +
        (spec.type_range ? ` (range ${spec.type_range[0] === spec.type_range[1] ? spec.type_range[0] : spec.type_range.join('–')})` : '') +
        `, χ²ᵣ ${spec.best.chi2_red.toFixed(2)}, ${spec.best.n_bins} channels` +
        (spec.verdict === 'match' ? '' : ` · ${spec.verdict}`)
      : (spec?.verdict ?? '')
  // y range from the plotted values, not their error bars: one noisy edge channel would otherwise flatten the spectrum
  const specY = [
    ...(byDate ? sxSpec.map((f) => (TO_FLAMBDA * f.flux_ujy!) / lam2(f)) : (spec?.binned.map((b) => TO_FLAMBDA * b.flambda) ?? [])),
    ...(spec?.template_curve?.flambda.map((f) => TO_FLAMBDA * f) ?? []),
  ]
  const [yLo, yHi] = [Math.min(...specY), Math.max(...specY)]
  const yPad = 0.1 * (yHi - yLo || 1)

  return (
    <div className="flex h-full flex-col text-xs">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-slate-700 px-2 py-1 whitespace-nowrap max-md:whitespace-normal">
        {(['lc', 'spec'] as const).map((t) => (
          <button key={t} className={`rounded px-2 py-0.5 max-md:min-h-11 max-md:px-4 ${tab === t ? 'bg-sky-700' : 'bg-slate-800'}`} onClick={() => setTab(t)}>
            {t === 'lc' ? 'Light curve' : 'Spectrum'}
          </button>
        ))}
        <button
          type="button"
          aria-label={AXIS_NOTE[tab]}
          aria-expanded={phone ? notesOpen : undefined}
          title={AXIS_NOTE[tab]}
          className="inline-flex cursor-help items-center justify-center focus:outline-none focus-visible:ring-1 focus-visible:ring-sky-400 max-md:h-11 max-md:w-11"
          onClick={() => setNotesOpen(!notesOpen)}
        >
          <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-500 font-serif text-[10px] text-slate-300 italic max-md:h-6 max-md:w-6">
            i
          </span>
        </button>
        {tab === 'lc' && (
          <>
            <label className="flex items-center gap-1 max-md:min-h-11">
              <input type="checkbox" checked={logY} onChange={(e) => setLogY(e.target.checked)} /> log y
            </label>
            {periods.length > 0 && (
              <label className="flex items-center gap-1 max-md:min-h-11" title={FOLD_NOTE}>
                Fold at
                <select className="rounded bg-slate-800 px-1 max-md:min-h-11" value={foldAt ?? ''} onChange={(e) => setFoldAt(e.target.value === '' ? null : Number(e.target.value))}>
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
                <label className="flex items-center gap-1 max-md:min-h-11" title={catalog?.source}>
                  <input type="checkbox" checked={showCatalog} onChange={(e) => setShowCatalog(e.target.checked)} /> WISE catalog photometry
                </label>
              )
            )}
            {sx.length > 0 && (
              <label className="flex items-center gap-1 max-md:min-h-11">
                <input type="checkbox" checked={showSpherex} onChange={(e) => setShowSpherex(e.target.checked)} /> SPHEREx (each point a different wavelength)
              </label>
            )}
          </>
        )}
        {tab === 'spec' && <span className="text-slate-300">{header}</span>}
        {tab === 'spec' && research && sxSpec.length > 0 && (
          <label className="flex items-center gap-1 max-md:min-h-11" title="Every SPHEREx frame instead of the channel averages, coloured by observation date">
            <input type="checkbox" checked={byDate} onChange={(e) => setByDate(e.target.checked)} /> by date
          </label>
        )}
        {tab === 'spec' && research && spec && spec.ranking.length > 1 && (
          <span className="text-slate-500">
            next: {spec.ranking.slice(1, 4).map((r) => `${r.label} (χ²ᵣ ${r.chi2_red.toFixed(2)})`).join(', ')}
          </span>
        )}
      </div>
      {phone && notesOpen && (
        <ul className="space-y-1 border-b border-slate-700 px-2 py-1 text-slate-300">
          <li>{AXIS_NOTE[tab]}</li>
          {tab === 'lc' && periods.length > 0 && <li>Fold at: {FOLD_NOTE}</li>}
          {tab === 'lc' && cat.length > 0 && <li>WISE catalog photometry: {catalog?.source}</li>}
        </ul>
      )}
      {/* overflow-hidden: Plotly's svg comes out a few px taller than its box and would scroll the page */}
      <div className="min-h-0 flex-1 overflow-hidden">
        {tab === 'lc' ? (
          <Plot
            className="h-full w-full"
            useResizeHandler
            data={lcTraces}
            layout={{
              ...DARK,
              ...phoneLayout,
              xaxis: { title: { text: folded ? `Phase (period ${foldAt.toFixed(1)} d)` : 'Date' } },
              yaxis: { title: { text: 'Brightness (µJy)' }, type: logY ? 'log' : 'linear' },
              annotations:
                settled && !lcTraces.length
                  ? [{ x: 0.5, y: 0.5, xref: 'paper', yref: 'paper', text: 'No brightness measurements for this object', showarrow: false, font: { size: 13, color: '#94a3b8' } }]
                  : [],
            }}
            config={config}
          />
        ) : (
          <Plot
            className="h-full w-full"
            useResizeHandler
            data={[
              byDate
                ? {
                    type: 'scatter',
                    mode: 'markers',
                    name: 'SPHEREx frames',
                    x: sxSpec.map((f) => f.wavelength_um!),
                    y: sxSpec.map((f) => (TO_FLAMBDA * f.flux_ujy!) / lam2(f)),
                    error_y: { type: 'data', array: sxSpec.map((f) => (TO_FLAMBDA * (f.flux_err_ujy ?? 0)) / lam2(f)), thickness: 1, width: 0, color: '#475569' },
                    text: sxSpec.map((f) => mjdToIso(f.mjd).slice(0, 10)),
                    marker: { color: sxSpec.map((f) => mjdToYear(f.mjd)), colorscale: 'Viridis', size: 5, colorbar: { title: { text: 'Year' }, thickness: 10 } },
                  }
                : {
                    type: 'scatter',
                    mode: 'markers',
                    name: 'SPHEREx (binned)',
                    x: spec?.binned.map((b) => b.wavelength_um) ?? [],
                    y: spec?.binned.map((b) => TO_FLAMBDA * b.flambda) ?? [],
                    error_y: { type: 'data', array: spec?.binned.map((b) => TO_FLAMBDA * b.err) ?? [], thickness: 1, width: 0 },
                    marker: { color: '#38bdf8', size: 6 },
                  },
              ...(spec?.template_curve
                ? [{
                    type: 'scatter',
                    mode: 'lines',
                    name: `Template ${spec.template_curve.label}`,
                    x: spec.template_curve.wavelength_um,
                    y: spec.template_curve.flambda.map((f) => TO_FLAMBDA * f),
                    line: { color: '#f472b6' },
                  }]
                : []),
            ]}
            layout={{
              ...DARK,
              ...phoneLayout,
              xaxis: { title: { text: 'Wavelength (µm)' }, range: [0.7, 5.1] },
              yaxis: { title: { text: 'F_λ (10⁻¹⁸ W m⁻² µm⁻¹)' }, range: specY.length ? [yLo - yPad, yHi + yPad] : undefined },
              shapes: MOLECULES.map(([, a, b], i) => ({
                type: 'rect', xref: 'x', yref: 'paper', x0: a, x1: b, y0: 0, y1: 1,
                fillcolor: i % 2 ? '#64748b' : '#475569', opacity: 0.18, line: { width: 0 }, layer: 'below',
              })),
              annotations: MOLECULES.map(([m, a, b], i) => ({
                x: (a + b) / 2, y: i % 2 ? 0.98 : 0.92, xref: 'x', yref: 'paper', text: m, hovertext: `${m} absorption, ${a}–${b} µm (approximate)`,
                showarrow: false, font: { size: 10, color: '#94a3b8' },
              })),
            }}
            config={config}
          />
        )}
      </div>
    </div>
  )
}
