import { useEffect, useState } from 'react'
import Discover from './components/Discover'
import Landing from './components/Landing'
import Learn from './components/Learn'
import TutorialDialog from './components/Tutorial'
import Workbench from './components/Workbench'
import { MODES, readUrl, writeUrl, type Mode } from './url'

const TITLES: Record<Mode, string> = { learn: 'Learn', explore: 'Explore', research: 'Research', discover: 'Discover' }

/** Mode switch (URL param `mode`, no router): landing page when absent. */
export default function App() {
  const [mode, setModeState] = useState(() => readUrl().mode)
  const [help, setHelp] = useState(false)
  useEffect(() => {
    const onPop = () => setModeState(readUrl().mode)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  const setMode = (m: Mode | null) => {
    writeUrl({ mode: m, frame: null }, true)
    setModeState(m)
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center gap-1 border-b border-slate-700 bg-slate-900 px-3 py-1.5">
        <button className="mr-3 font-semibold text-sky-300" onClick={() => setMode(null)}>
          Ultracool Browser
        </button>
        <nav aria-label="Modes" className="flex gap-1">
          {MODES.map((m) => (
            <button
              key={m}
              aria-current={m === mode ? 'page' : undefined}
              className={`rounded px-3 py-1 text-sm ${m === mode ? 'bg-sky-700' : 'text-slate-300 hover:bg-slate-800'}`}
              onClick={() => setMode(m)}
            >
              {TITLES[m]}
            </button>
          ))}
        </nav>
        <button className="ml-auto rounded px-3 py-1 text-sm text-slate-300 hover:bg-slate-800" onClick={() => setHelp(true)}>
          ? Help
        </button>
      </header>
      <main className="min-h-0 flex-1">
        {mode === null ? (
          <Landing onMode={setMode} />
        ) : mode === 'learn' ? (
          <Learn />
        ) : mode === 'discover' ? (
          <Discover />
        ) : (
          <Workbench key={mode} mode={mode} />
        )}
      </main>
      <TutorialDialog open={help} onClose={() => setHelp(false)} />
    </div>
  )
}
