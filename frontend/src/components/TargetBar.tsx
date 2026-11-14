import { useRef, useState, type ReactNode } from 'react'
import type { Resolved } from '../api'

export type Example = { q: string; label: string }
/** pre-computed by scripts/prewarm.py (keep in sync), so they open without waiting */
export const EXAMPLES: Example[] = [
  { q: "Barnard's Star", label: "Barnard's Star" },
  { q: 'eps Ind B', label: 'eps Ind B' },
  { q: 'WISE J085510.83-071442.5', label: 'WISE 0855' },
  { q: 'WISE J231728.42-665959.3', label: 'WISE J2317−6659 (featured)' },
  { q: 'WISEA J153429.75-104303.3', label: 'WISEA J1534−1043' },
  { q: 'RW Aur', label: 'RW Aur' },
  { q: 'R Dra', label: 'R Dra' },
  { q: 'AL Boo', label: 'AL Boo' },
]

type Props = {
  initial: string
  resolved: Resolved | null
  busy: boolean
  error: string | null
  badge?: ReactNode
  onSubmit: (q: string) => void
  /** pre-computed picks in a dropdown (default: EXAMPLES) */
  examples?: Example[]
  examplesLabel?: string
  /** extra controls after the examples */
  children?: ReactNode
}

export default function TargetBar({ initial, resolved, busy, error, badge, onSubmit, examples = EXAMPLES, examplesLabel = 'Examples', children }: Props) {
  const [q, setQ] = useState(initial)
  const menu = useRef<HTMLDetailsElement>(null)
  const go = (s: string) => {
    setQ(s)
    if (s.trim()) onSubmit(s.trim())
  }
  const pm = resolved ? Math.hypot(resolved.pmra_masyr, resolved.pmdec_masyr) / 1000 : 0
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-700 bg-slate-900 px-3 py-2">
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
      {/* a disclosure, not a <select>: arrow keys on a closed select fire change and would load every example on the way */}
      <details ref={menu} className="relative text-xs">
        <summary className="cursor-pointer list-none rounded bg-slate-700 px-2 py-1 hover:bg-slate-600">{examplesLabel} ▾</summary>
        <ul className="absolute z-40 mt-1 w-64 rounded border border-slate-600 bg-slate-900 p-1 shadow-xl">
          {examples.map((x) => (
            <li key={x.q}>
              <button
                className="flex w-full items-center justify-between gap-2 rounded px-2 py-1 text-left hover:bg-slate-700 focus:bg-slate-700 focus:outline-none"
                onClick={() => {
                  menu.current!.open = false
                  go(x.q)
                }}
              >
                {x.label}
                <span className="text-[10px] text-emerald-400">ready instantly</span>
              </button>
            </li>
          ))}
        </ul>
      </details>
      {children}
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
