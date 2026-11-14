import type { ReactNode } from 'react'
import type { Summary } from '../api'
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

/** Explore mode: the summary as four yes/no badges plus the backend's plain-English sentences. */
export default function FoundPanel({ summary, note }: { summary: Summary | null; note: string | null }) {
  if (!summary) return <p className="p-2 text-xs text-slate-500">{note}</p>
  const { motion, color, variability, spectrum } = summary
  const pm = motion.pm_total_arcsec_yr
  const spec = spectrum?.verdict === 'match' && spectrum.best ? spectrum.best.label : null
  return (
    <div className="space-y-2 p-2 text-xs">
      <div className="grid grid-cols-2 gap-1">
        <Badge
          q={<>Moves? (<Term k="proper motion" />)</>}
          a={motion.verdict === 'moving' ? `Yes${pm !== null ? `, ${pm.toFixed(2)}″/yr` : ''}` : motion.verdict === 'not moving' ? 'No' : 'Not sure'}
          tone={motion.verdict === 'moving' ? 'yes' : motion.verdict === 'not moving' ? 'no' : 'unknown'}
        />
        <Badge
          q={<>Cold / red? (<Term k="W1−W2" />)</>}
          a={
            color.verdict === 'extremely red (Y/late-T dwarf-like)' ? 'Very cold!' : color.verdict === 'red (L/T dwarf-like)' ? 'Cool, brown-dwarf-like' : color.verdict === 'normal star colors' ? 'No, normal star' : 'Not sure'
          }
          tone={color.verdict.startsWith('extremely') || color.verdict.startsWith('red') ? 'yes' : color.verdict === 'normal star colors' ? 'no' : 'unknown'}
        />
        <Badge
          q={<>Brightness changes? (<Term k="light curve" />)</>}
          a={
            variability.verdict === 'periodic variable'
              ? `Yes, repeats${variability.period_days ? ` every ~${Math.round(variability.period_days)} d` : ''}`
              : variability.verdict === 'irregular variable' ? 'Yes, irregularly' : variability.verdict === 'constant' ? 'No' : 'Not sure'
          }
          tone={variability.verdict.endsWith('variable') ? 'yes' : variability.verdict === 'constant' ? 'no' : 'unknown'}
        />
        <Badge q={<><Term k="spectrum" /> type</>} a={spec ?? 'Not sure'} tone={spec ? 'yes' : 'unknown'} />
      </div>
      <ul className="list-disc space-y-1 pl-4 text-slate-300">
        {summary.plain.map((s) => <li key={s}>{s}</li>)}
      </ul>
    </div>
  )
}
