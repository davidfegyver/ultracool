import type { ReactNode } from 'react'
import { exportCsvUrl, type KnownAsteroid, type Sequence, type Summary } from '../api'
import MotionPlot from './MotionPlot'
import Pending from './Pending'

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

/** Research mode: summary numbers with errors, motion plot, known asteroids (with `showAsteroids`) and the CSV export. */
export default function ResearchPanel({ seq, summary, note, busy, showAsteroids }: {
  seq: Sequence | null
  summary: Summary | null
  note: string | null
  busy: boolean
  showAsteroids: boolean
}) {
  const { motion: m, color: c, variability: v, spectrum: s } = summary ?? {}
  return (
    <div className="p-2 text-xs">
      <div className="flex items-center gap-2">
        <a
          className="rounded bg-sky-700 px-2 py-1 hover:bg-sky-600 aria-disabled:pointer-events-none aria-disabled:opacity-50"
          aria-disabled={!seq}
          href={seq ? exportCsvUrl(seq.id) : undefined}
          download
        >
          ⤓ Download CSV
        </a>
        <span className="text-slate-500">brightness for every frame, with the source file of each</span>
      </div>
      {!summary && <Pending note={note} busy={busy} className="mt-2" />}
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
      <PhotometryTables color={c} variability={v} spectrum={s} />
      {showAsteroids && summary?.asteroids && <AsteroidList asteroids={summary.asteroids} />}
    </div>
  )
}

/** Colour, variability and spectral-typing tables (target summary or probe). */
export function PhotometryTables({ color: c, variability: v, spectrum: s }: Partial<Pick<Summary, 'color' | 'variability' | 'spectrum'>>) {
  return (
    <>
      {c && (
        <>
          <H>Color ({c.verdict})</H>
          <Table rows={[['W1−W2 (mag)', `${c.w1_w2_is_lower_limit ? '≥ ' : ''}${fmt(c.w1_w2, 2)} ± ${fmt(c.w1_w2_err, 2)}`]]} />
        </>
      )}
      {v && (
        <>
          <H>
            Variability ({v.verdict}
            {v.source && `, ${v.source === 'catalog' ? 'WISE catalog photometry' : 'our photometry'}`})
          </H>
          {v.source_note && <p className="text-slate-400">{v.source_note}</p>}
          <Table
            rows={[
              [
                'Period (d)',
                `${fmt(v.period_days)}${v.period_alternatives_days?.length ? ` or ${v.period_alternatives_days.map((a) => fmt(a)).join(' or ')}` : ''}${v.period_alias_warning ? ' ⚠' : ''}`,
              ],
              ...(v.fap !== undefined ? [['False-alarm prob.', v.fap === null ? '—' : v.fap.toExponential(1)] as [string, string]] : []),
              ...Object.entries(v.bands).map(
                ([b, x]) => [`${b}: n, χ²ᵣ, amp (mag)`, `${x.n}, ${fmt(x.chi2_red, 2)}, ${fmt(x.amplitude_mag, 2)}`] as [string, string],
              ),
            ]}
          />
          {v.period_alias_warning && <p className="text-amber-400">⚠ This period might be an artefact of WISE visiting only every 6 months.</p>}
        </>
      )}
      {s && (
        <>
          <H>Spectrum ({s.verdict})</H>
          <Table
            rows={[
              ...(s.type_range ? [['Type range', s.type_range[0] === s.type_range[1] ? s.type_range[0] : s.type_range.join('–')] as [string, string]] : []),
              ...s.ranking.map((r): [string, string] => [r.label, `χ²ᵣ=${r.chi2_red.toFixed(2)} n=${r.n_bins}`]),
            ]}
          />
        </>
      )}
    </>
  )
}

/** Known solar-system objects in the field (from the summary). */
function AsteroidList({ asteroids }: { asteroids: KnownAsteroid[] }) {
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
