import Plotly from 'plotly.js-dist-min'
import { useEffect, useRef, useState } from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'
import { getSpectrum, type Sequence, type Spectrum } from '../api'
import { ALL_BANDS } from './Player'

const Plot = createPlotlyComponent(Plotly)

// approximate molecular absorption bands in ultracool-dwarf spectra (µm)
const MOLECULES: [string, number, number][] = [
  ['H₂O', 1.1, 1.2], ['H₂O', 1.33, 1.5], ['H₂O', 1.75, 2.05], ['H₂O', 2.5, 3.0],
  ['CH₄', 1.6, 1.8], ['CH₄', 2.15, 2.5], ['CH₄', 3.2, 3.5],
  ['CO', 2.29, 2.4], ['CO', 4.5, 4.9], ['CO₂', 4.2, 4.35], ['NH₃', 2.9, 3.1],
]
const COLORS = ['#f87171', '#fb923c', '#a78bfa', '#818cf8', '#38bdf8', '#2dd4bf', '#4ade80', '#facc15']
const DARK = {
  paper_bgcolor: '#0f172a',
  plot_bgcolor: '#0f172a',
  font: { color: '#cbd5e1', size: 11 },
  margin: { l: 60, r: 10, t: 10, b: 40 },
  legend: { orientation: 'h' as const, y: 1.12 },
}
const SPECTRUM_REFRESH_MS = 10_000

export default function PlotsPanel({ seq }: { seq: Sequence | null }) {
  const [tab, setTab] = useState<'lc' | 'spec'>('lc')
  // linear by default: faint targets have zero or negative fluxes, which a log axis silently drops
  const [logY, setLogY] = useState(false)
  const [spec, setSpec] = useState<Spectrum | null>(null)
  const last = useRef({ id: '', n: -1, t: 0 })

  // refetch when new frames arrive, at most every 10 s (and always once the job settles)
  const n = seq?.frames.length ?? 0
  useEffect(() => {
    if (!seq) return setSpec(null)
    const l = last.current
    const settled = seq.status === 'done' || seq.status === 'error'
    if (l.id === seq.id && (l.n === n || (!settled && Date.now() - l.t < SPECTRUM_REFRESH_MS))) return
    last.current = { id: seq.id, n, t: Date.now() }
    getSpectrum(seq.id).then(setSpec).catch(() => setSpec(null))
  }, [seq, n])

  const frames = (seq?.frames ?? []).filter((f) => f.flux_ujy !== null)
  const lcTraces = ALL_BANDS.map((b, i) => {
    const fs = frames.filter((f) => f.band === b)
    return {
      type: 'scatter' as const,
      mode: 'markers' as const,
      name: b,
      x: fs.map((f) => f.date),
      y: fs.map((f) => f.flux_ujy),
      error_y: { type: 'data' as const, array: fs.map((f) => f.flux_err_ujy ?? 0), thickness: 1, width: 0 },
      marker: { color: COLORS[i], symbol: fs.map((f) => (f.flagged ? 'circle-open' : 'circle')), size: 6 },
      text: fs.map((f) => `${f.wavelength_um?.toFixed(2)} µm${f.flagged ? ' (flagged)' : ''}`),
    }
  }).filter((t) => t.x.length)

  const header = spec?.best
    ? `Best match: ${spec.best.label} (p=${spec.best.prob.toFixed(2)}, χ²ᵣ=${spec.best.chi2_red.toFixed(2)}, ${spec.best.n_bins} bins)` +
      (spec.verdict === 'match' ? '' : ` · ${spec.verdict}`)
    : (spec?.verdict ?? '')

  return (
    <div className="flex h-full flex-col text-xs">
      <div className="flex items-center gap-2 border-b border-slate-700 px-2 py-1">
        {(['lc', 'spec'] as const).map((t) => (
          <button key={t} className={`rounded px-2 py-0.5 ${tab === t ? 'bg-sky-700' : 'bg-slate-800'}`} onClick={() => setTab(t)}>
            {t === 'lc' ? 'Light curve' : 'Spectrum'}
          </button>
        ))}
        {tab === 'lc' && (
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={logY} onChange={(e) => setLogY(e.target.checked)} /> log y
          </label>
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
            layout={{ ...DARK, xaxis: { title: { text: 'Date' } }, yaxis: { title: { text: 'Flux (µJy, aperture-corrected)' }, type: logY ? 'log' : 'linear' } }}
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
