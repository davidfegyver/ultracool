import { useState, type ReactNode } from 'react'
import { exportCsvUrl, type KnownAsteroid, type Sequence, type Summary } from '../api'
import { downloadBlob } from '../csv'
import MotionPlot from './MotionPlot'

const fmt = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? '—' : v.toFixed(d))
const pm = (v: number | null, e: number | null) => `${fmt(v)} ± ${fmt(e)}`

function Table({ rows }: { rows: [ReactNode, ReactNode][] }) {
  return (
    <table className="w-full">
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i} className="border-b border-slate-800">
            <th className="py-0.5 pr-2 text-left font-normal text-slate-400">{k}</th>
            <td className="text-right font-mono">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const H = ({ children }: { children: ReactNode }) => <h4 className="mt-2 font-semibold text-slate-300">{children}</h4>

/** Research mode: summary numbers with errors, motion plot, known asteroids and the CSV export. */
export default function ResearchPanel({ seq, summary, note }: { seq: Sequence | null; summary: Summary | null; note: string | null }) {
  const [csvNote, setCsvNote] = useState<string | null>(null)
  const download = async () => {
    if (!seq) return
    setCsvNote('Preparing…')
    const r = await fetch(exportCsvUrl(seq.id)).catch(() => null)
    if (!r?.ok) return setCsvNote(r?.status === 404 ? 'CSV export not available yet on this server' : `Export failed${r ? ` (${r.status})` : ''}`)
    downloadBlob(await r.blob(), `ultracool_${seq.id}.csv`)
    setCsvNote(null)
  }
  const { motion: m, color: c, variability: v, spectrum: s } = summary ?? {}
  return (
    <div className="p-2 text-xs">
      <div className="flex items-center gap-2">
        <button className="rounded bg-sky-700 px-2 py-1 enabled:hover:bg-sky-600 disabled:opacity-50" disabled={!seq} onClick={download}>
          ⤓ Download CSV
        </button>
        <span className="text-slate-500">{csvNote ?? 'per-frame photometry with provenance'}</span>
      </div>
      {!summary && <p className="mt-2 text-slate-500">{note}</p>}
      {m && (
        <>
          <H>Motion ({m.verdict})</H>
          <Table
            rows={[
              ['μα* (mas/yr)', pm(m.pmra_masyr, m.pmra_err_masyr)],
              ['μδ (mas/yr)', pm(m.pmdec_masyr, m.pmdec_err_masyr)],
              ['μ total (″/yr)', fmt(m.pm_total_arcsec_yr, 3)],
              ['Significance (σ)', fmt(m.significance_sigma)],
              ['Baseline (yr) / epochs', `${fmt(m.baseline_yr)} / ${m.n_epochs ?? '—'}`],
              ['Catalog μα*, μδ', m.catalog ? `${fmt(m.catalog.pmra_masyr)}, ${fmt(m.catalog.pmdec_masyr)}` : '—'],
              ['Consistent with catalog', m.consistent_with_catalog === null ? '—' : m.consistent_with_catalog ? 'yes' : 'NO'],
            ]}
          />
          <MotionPlot motion={m} />
        </>
      )}
      {c && (
        <>
          <H>Color ({c.verdict})</H>
          <Table rows={[['W1−W2 (mag)', `${c.w1_w2_is_lower_limit ? '> ' : ''}${fmt(c.w1_w2, 2)} ± ${fmt(c.w1_w2_err, 2)}`]]} />
        </>
      )}
      {v && (
        <>
          <H>Variability ({v.verdict})</H>
          <Table
            rows={[
              ['Period (d)', `${fmt(v.period_days)}${v.period_alias_warning ? ' ⚠' : ''}`],
              ...(v.fap !== undefined ? [['False-alarm prob.', v.fap === null ? '—' : v.fap.toExponential(1)] as [string, string]] : []),
              ...Object.entries(v.bands).map(
                ([b, x]) => [`${b}: n, χ²ᵣ, amp (mag)`, `${x.n}, ${fmt(x.chi2_red, 2)}, ${fmt(x.amplitude_mag, 2)}`] as [string, string],
              ),
            ]}
          />
          {v.period_alias_warning && <p className="text-amber-400">⚠ The period may be an alias of WISE's 6-month / 1-year visit cadence.</p>}
        </>
      )}
      {s && (
        <>
          <H>Spectrum ({s.verdict})</H>
          <Table rows={s.ranking.map((r) => [r.label, `p=${r.prob.toFixed(2)} χ²ᵣ=${r.chi2_red.toFixed(2)} n=${r.n_bins}`])} />
        </>
      )}
      {summary?.asteroids && <AsteroidList asteroids={summary.asteroids} />}
    </div>
  )
}

/** Known solar-system objects in the field (from the summary). */
export function AsteroidList({ asteroids }: { asteroids: KnownAsteroid[] }) {
  return (
    <>
      <H>Known asteroids in field</H>
      {asteroids.length ? (
        <Table rows={asteroids.map((a) => [a.name, `${a.ra.toFixed(4)} ${a.dec.toFixed(4)} · MJD ${a.mjd.toFixed(2)} · ${fmt(a.rate_arcsec_h)}″/h`])} />
      ) : (
        <p className="text-slate-500">None</p>
      )}
    </>
  )
}
