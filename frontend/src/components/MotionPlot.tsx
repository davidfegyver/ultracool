import type { Summary } from '../api'
import { DARK, Plot } from './PlotsPanel'

const year = (mjd: number) => 2000 + (mjd - 51544.5) / 365.25

/** Measured positions (offsets from their mean, arcsec) vs time, with the fitted proper motion as lines. */
export default function MotionPlot({ motion }: { motion: Summary['motion'] }) {
  const pts = motion.points
  if (!pts.length) return <p className="text-slate-500">No measured positions</p>
  const ra0 = pts.reduce((s, p) => s + p.ra, 0) / pts.length
  const dec0 = pts.reduce((s, p) => s + p.dec, 0) / pts.length
  const cosd = Math.cos((dec0 * Math.PI) / 180)
  const t = pts.map((p) => year(p.mjd))
  const t0 = t.reduce((a, b) => a + b, 0) / t.length
  const tr = [Math.min(...t), Math.max(...t)]
  const axes = [
    { name: 'ΔRA·cosδ', color: '#38bdf8', y: pts.map((p) => (p.ra - ra0) * cosd * 3600), pm: motion.pmra_masyr },
    { name: 'ΔDec', color: '#f472b6', y: pts.map((p) => (p.dec - dec0) * 3600), pm: motion.pmdec_masyr },
  ]
  return (
    <Plot
      className="h-56 w-full"
      useResizeHandler
      data={axes.flatMap((a) => [
        {
          type: 'scatter' as const,
          mode: 'markers' as const,
          name: a.name,
          x: t,
          y: a.y,
          error_y: { type: 'data' as const, array: pts.map((p) => p.err_arcsec), thickness: 1, width: 0 },
          marker: { color: a.color, size: 5 },
          text: pts.map((p) => p.band),
        },
        // shortcut: line drawn through the mean point (exact for an unweighted fit); the backend's weighted intercept is not in the contract
        ...(a.pm === null
          ? []
          : [{ type: 'scatter' as const, mode: 'lines' as const, name: `${a.name} fit`, x: tr, y: tr.map((x) => (a.pm! / 1000) * (x - t0)), line: { color: a.color, dash: 'dash' as const } }]),
      ])}
      layout={{ ...DARK, margin: { l: 45, r: 5, t: 5, b: 50 }, legend: { orientation: 'h', y: -0.2 }, yaxis: { title: { text: 'Offset (″)' } } }}
      config={{ displaylogo: false, responsive: true, displayModeBar: false }}
    />
  )
}
