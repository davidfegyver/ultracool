import { useState, type ReactNode } from 'react'
import type { Resolved } from '../api'

export const TEST_TARGETS = ["Barnard's Star", 'eps Ind B', 'WISE J085510.83-071442.5', 'RW Aur', 'R Dra']

type Props = {
  initial: string
  resolved: Resolved | null
  busy: boolean
  error: string | null
  badge?: ReactNode
  onSubmit: (q: string) => void
}

export default function TargetBar({ initial, resolved, busy, error, badge, onSubmit }: Props) {
  const [q, setQ] = useState(initial)
  const go = (s: string) => {
    setQ(s)
    if (s.trim()) onSubmit(s.trim())
  }
  const pm = resolved ? Math.hypot(resolved.pmra_masyr, resolved.pmdec_masyr) / 1000 : 0
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-700 bg-slate-900 px-3 py-2">
      <span className="mr-2 font-semibold text-sky-300">Ultracool Browser</span>
      <form
        className="flex gap-1"
        onSubmit={(e) => {
          e.preventDefault()
          go(q)
        }}
      >
        <input
          aria-label="Object name or coordinates"
          className="w-72 rounded bg-slate-800 px-2 py-1 text-sm"
          placeholder="Name or RA Dec (deg or hms dms)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="rounded bg-sky-700 px-3 py-1 text-sm hover:bg-sky-600" disabled={busy}>
          Go
        </button>
      </form>
      {TEST_TARGETS.map((t) => (
        <button key={t} className="rounded bg-slate-700 px-2 py-1 text-xs hover:bg-slate-600" onClick={() => go(t)}>
          {t}
        </button>
      ))}
      <div className="ml-auto flex items-center gap-3 text-sm">
        {busy && <span className="text-slate-400">Resolving…</span>}
        {error && <span className="text-red-400">{error}</span>}
        {resolved && (
          <span>
            <b>{resolved.name ?? `${resolved.ra.toFixed(5)} ${resolved.dec.toFixed(5)}`}</b>
            {resolved.otype && <span className="ml-2 text-slate-400">{resolved.otype}</span>}
            {resolved.sptype && <span className="ml-2 text-slate-400">{resolved.sptype}</span>}
            <span className="ml-2 text-slate-400">PM {pm.toFixed(3)}″/yr</span>
          </span>
        )}
        {badge}
      </div>
    </div>
  )
}
