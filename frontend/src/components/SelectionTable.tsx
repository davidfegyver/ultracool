import type { Source } from 'aladin-lite'
import { useState } from 'react'

const csvCell = (v: unknown) => {
  const s = v === null || v === undefined ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** Sources picked with the rectangle selector: one tab per catalog, columns = source data keys, CSV export. */
export default function SelectionTable({ groups, onClose }: { groups: Source[][]; onClose: () => void }) {
  const tabs = groups.filter((g) => g.length)
  const [i, setI] = useState(0)
  const rows = tabs[i] ?? []
  const cols = [...new Set(rows.flatMap((s) => Object.keys(s.data)))]
  const name = (g: Source[]) => g[0]?.catalog?.name ?? 'Catalog'

  const download = () => {
    const csv = [cols.map(csvCell).join(','), ...rows.map((s) => cols.map((c) => csvCell(s.data[c])).join(','))].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${name(rows).replace(/\W+/g, '_')}_selection.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="absolute inset-x-4 bottom-4 z-10 flex max-h-[60%] flex-col rounded border border-slate-600 bg-slate-900/95 text-xs shadow-xl">
      <div className="flex items-center gap-1 border-b border-slate-700 px-2 py-1">
        {tabs.map((g, j) => (
          <button key={j} className={`rounded px-2 py-0.5 ${j === i ? 'bg-sky-700' : 'bg-slate-800'}`} onClick={() => setI(j)}>
            {name(g)} ({g.length})
          </button>
        ))}
        {!tabs.length && <span className="text-slate-400">No catalog sources inside the rectangle</span>}
        <span className="ml-auto" />
        {rows.length > 0 && <button className="rounded bg-slate-700 px-2 py-0.5" onClick={download}>Download CSV</button>}
        <button className="rounded bg-slate-700 px-2 py-0.5" aria-label="Close selection" onClick={onClose}>✕</button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full whitespace-nowrap">
          <thead className="sticky top-0 bg-slate-800 text-left text-slate-400">
            <tr>{cols.map((c) => <th key={c} className="px-1">{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((s, k) => (
              <tr key={k} className="hover:bg-slate-800">
                {cols.map((c) => <td key={c} className="px-1">{String(s.data[c] ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
