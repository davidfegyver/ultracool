import type { ReactNode } from 'react'
import type { Summary } from '../api'
import Pending from './Pending'
import Term from './Term'

type Tone = 'yes' | 'no' | 'unknown'
const TONE: Record<Tone, string> = { yes: 'bg-emerald-800 text-emerald-100', no: 'bg-slate-700 text-slate-300', unknown: 'bg-slate-800 text-slate-500' }

function Badge({ q, a, tone }: { q: ReactNode; a: string; tone: Tone }) {
  return (
    <div className={`rounded px-2 py-1 ${TONE[tone]}`}>
      <div className="text-[10px] tracking-wide uppercase opacity-80">{q}</div>
      <div className="text-sm font-semibold">{a}</div>
    </div>
  )
}

/** Explore mode: the summary as yes/no badges plus the backend's plain-English sentences. Without `motion` (probe
 * results) the "Moves?" badge is left out. */
export default function FoundPanel({ summary, note, busy }: {
  summary: (Pick<Summary, 'color' | 'variability' | 'spectrum' | 'plain'> & { motion?: Summary['motion'] }) | null
  note: string | null
  busy: boolean
}) {
  if (!summary) return <Pending note={note} busy={busy} className="p-2" />
  const { motion, color, variability, spectrum } = summary
  const pm = motion?.pm_total_arcsec_yr ?? null
  const spec = spectrum?.verdict === 'match' && spectrum.best ? spectrum.best.label : null
  const period = variability.period_days
  const alts = variability.period_alternatives_days ?? []
  return (
    <div className="space-y-2 p-2 text-xs">
      <div className="grid grid-cols-2 gap-1">
        {motion && (
          <Badge
            q={<>Moves? (<Term k="proper motion" />)</>}
            a={motion.verdict === 'moving' ? `Yes${pm !== null ? `, ${pm.toFixed(2)}″/yr` : ''}` : motion.verdict === 'not moving' ? 'No' : 'Not sure'}
            tone={motion.verdict === 'moving' ? 'yes' : motion.verdict === 'not moving' ? 'no' : 'unknown'}
          />
        )}
        <Badge
          q={<>Cold / red? (<Term k="W1−W2" />)</>}
          a={
            {
              'extremely red (Y/late-T dwarf-like)': 'Very cold!',
              'very red (T dwarf-like)': 'Red, like T dwarfs',
              'red (L/T dwarf-like)': 'Red, like brown dwarfs',
              'normal star colors': 'No, normal star',
              'insufficient data': 'Not sure',
            }[color.verdict] ?? 'Not sure'
          }
          tone={color.verdict === 'insufficient data' ? 'unknown' : color.verdict === 'normal star colors' ? 'no' : 'yes'}
        />
        <Badge
          q={<>Brightness changes? (<Term k="light curve" />)</>}
          a={
            variability.verdict === 'periodic variable'
              ? `Yes, repeats${period ? ` every ~${Math.round(period)} d${alts.length ? ` (or ${alts.map((a) => Math.round(a)).join(' or ')} d)` : ''}` : ''}`
              : variability.verdict === 'irregular variable' ? 'Yes, irregularly' : variability.verdict === 'constant' ? 'No' : 'Not sure'
          }
          tone={variability.verdict.endsWith('variable') ? 'yes' : variability.verdict === 'constant' ? 'no' : 'unknown'}
        />
        <Badge q={<><Term k="spectrum" /> type</>} a={spec ?? 'Not sure'} tone={spec ? 'yes' : 'unknown'} />
      </div>
      {variability.source === 'catalog' && (
        <p className="text-amber-300" title={variability.source_note}>
          Brightness comes from the WISE catalog: this object is too bright for our own measurements.
        </p>
      )}
      <ul className="list-disc space-y-1 pl-4 text-slate-300">
        {summary.plain.map((s) => <li key={s}>{s}</li>)}
      </ul>
    </div>
  )
}
