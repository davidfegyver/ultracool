import { useState } from 'react'
import type { SeqOptions } from '../api'

const isoDate = (mjd: string) => (mjd === '' || isNaN(Number(mjd)) ? '' : new Date((Number(mjd) - 40587) * 864e5).toISOString().slice(0, 10))
const MAX_EXPOSURE_SPAN_D = 30 // backend rejects per-exposure WISE frames over longer windows

/** Re-run the sequence restricted to an MJD window, optionally with every WISE exposure (asteroids, transients). */
export default function TimeWindow({ value, onApply }: { value: SeqOptions; onApply: (o: SeqOptions) => void }) {
  const [min, setMin] = useState(value.mjd_min?.toString() ?? '')
  const [max, setMax] = useState(value.mjd_max?.toString() ?? '')
  const [exposures, setExposures] = useState(!!value.wise_exposures)
  const span = Number(max) - Number(min)
  const bothSet = min !== '' && max !== ''
  const invalid = bothSet && !(span > 0)
  const exposuresOk = bothSet && span > 0 && span <= MAX_EXPOSURE_SPAN_D
  const active = value.mjd_min !== undefined || value.mjd_max !== undefined
  return (
    <form
      className="space-y-1 p-2 text-xs"
      onSubmit={(e) => {
        e.preventDefault()
        onApply({
          ...(min !== '' && { mjd_min: Number(min) }),
          ...(max !== '' && { mjd_max: Number(max) }),
          ...(exposures && exposuresOk && { wise_exposures: true }),
        })
      }}
    >
      {([['From MJD', min, setMin], ['To MJD', max, setMax]] as const).map(([label, v, set]) => (
        <label key={label} className="flex items-center gap-2">
          <span className="w-16">{label}</span>
          <input type="number" step="any" placeholder="e.g. 55400" className="w-28 rounded border border-slate-600 bg-slate-800 px-1" value={v} onChange={(e) => set(e.target.value)} />
          <span className="text-slate-500">{isoDate(v)}</span>
        </label>
      ))}
      <label className={`flex items-center gap-1 ${exposuresOk ? '' : 'text-slate-500'}`}>
        <input type="checkbox" disabled={!exposuresOk} checked={exposures && exposuresOk} onChange={(e) => setExposures(e.target.checked)} />
        Every WISE exposure as its own frame (window ≤ {MAX_EXPOSURE_SPAN_D} days)
      </label>
      <div className="flex items-center gap-2">
        <button className="rounded bg-sky-700 px-2 py-0.5 disabled:opacity-50" disabled={invalid || (min === '' && max === '')}>
          Fetch window
        </button>
        {active && (
          <button
            type="button"
            className="rounded bg-slate-700 px-2 py-0.5"
            onClick={() => {
              setMin('')
              setMax('')
              setExposures(false)
              onApply({})
            }}
          >
            All 16 years
          </button>
        )}
        {invalid && <span className="text-red-400">End must be after start</span>}
      </div>
    </form>
  )
}
