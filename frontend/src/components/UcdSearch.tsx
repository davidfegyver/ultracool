import { useEffect, useState } from 'react'
import { searchUcds, ucdDatasets, type Ucd } from '../api'

type Props = {
  onPick: (u: Ucd) => void
  onShowOnSky: (rows: Ucd[]) => void
}

/** Reverse search of the SPIFF ultracool-dwarf catalog by spectral class. */
export default function UcdSearch({ onPick, onShowOnSky }: Props) {
  const [min, setMin] = useState('T8')
  const [max, setMax] = useState('Y1')
  const [dataset, setDataset] = useState('')
  const [datasets, setDatasets] = useState<string[]>([])
  const [rows, setRows] = useState<Ucd[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    ucdDatasets().then(setDatasets).catch(() => setDatasets([]))
  }, [])

  const search = async () => {
    setError(null)
    try {
      setRows(await searchUcds({ spt_min: min, spt_max: max, dataset }))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="flex h-full flex-col text-xs">
      <form
        className="flex flex-wrap items-center gap-1 border-b border-slate-700 px-2 py-1"
        onSubmit={(e) => {
          e.preventDefault()
          search()
        }}
      >
        <span className="font-semibold text-slate-300">UCD search</span>
        <input aria-label="Minimum spectral type" className="w-12 rounded bg-slate-800 px-1" value={min} onChange={(e) => setMin(e.target.value)} />
        –
        <input aria-label="Maximum spectral type" className="w-12 rounded bg-slate-800 px-1" value={max} onChange={(e) => setMax(e.target.value)} />
        <select aria-label="Dataset" className="rounded bg-slate-800" value={dataset} onChange={(e) => setDataset(e.target.value)}>
          <option value="">All datasets</option>
          {datasets.map((d) => <option key={d}>{d}</option>)}
        </select>
        <button className="rounded bg-sky-700 px-2">Search</button>
        {rows && rows.length > 0 && (
          <button type="button" className="rounded bg-slate-700 px-2" onClick={() => onShowOnSky(rows)}>
            Show on sky
          </button>
        )}
        {rows && <span className="text-slate-500">{rows.length} rows</span>}
        {error && <span className="text-red-400">{error}</span>}
      </form>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full">
          <thead className="sticky top-0 bg-slate-800 text-left text-slate-400">
            <tr><th className="px-1">Designation</th><th>SPIFF</th><th>Lit.</th><th>χ²ᵣ</th><th>Dataset</th></tr>
          </thead>
          <tbody>
            {rows?.map((u) => (
              <tr key={u.designation} className="cursor-pointer hover:bg-slate-800" onClick={() => onPick(u)}>
                <td className="px-1">{u.designation}</td>
                <td>{u.spiff_autotype}</td>
                <td>{u.literature_spectral_type ?? ''}</td>
                <td>{u.spiff_chi2_r ?? ''}</td>
                <td className="text-slate-500">{u.dataset}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
