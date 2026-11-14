import type { Aladin } from 'aladin-lite'
import { useEffect, useState } from 'react'
import { resolveTarget, type Resolved } from './api'
import LayersPanel from './components/LayersPanel'
import SkyView from './components/SkyView'
import TargetBar from './components/TargetBar'
import { readUrl, writeUrl } from './url'

const initialUrl = readUrl()
const DEFAULT_TARGET = "Barnard's Star"

export default function App() {
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aladin, setAladin] = useState<Aladin | null>(null)

  const lookup = async (q: string) => {
    setBusy(true)
    setError(null)
    try {
      setResolved(await resolveTarget(q))
      writeUrl({ target: q, ra: null, dec: null })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    const { ra, dec, target } = initialUrl
    if (ra !== null && dec !== null) {
      setResolved({ name: target, ra, dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: null })
    } else {
      lookup(target ?? DEFAULT_TARGET)
    }
  }, [])

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <TargetBar
        initial={initialUrl.target ?? DEFAULT_TARGET}
        resolved={resolved}
        busy={busy}
        error={error}
        onSubmit={(q) => {
          writeUrl({ frame: null })
          lookup(q)
        }}
      />
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          {resolved && (
            <SkyView ra={resolved.ra} dec={resolved.dec} fov={initialUrl.fov ?? 0.25} onReady={setAladin} />
          )}
        </div>
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-700 bg-slate-900">
          <LayersPanel aladin={aladin} frames={<p className="px-2 py-1 text-xs text-slate-500">No frames yet</p>} />
        </aside>
      </div>
    </div>
  )
}
