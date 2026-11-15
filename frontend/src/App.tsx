import { useEffect, useState } from 'react'
import Discover from './components/Discover'
import Landing from './components/Landing'
import Learn from './components/Learn'
import TutorialDialog from './components/Tutorial'
import Workbench from './components/Workbench'
import { PHONE_QUERY, useIsPhone } from './hooks'
import { MODES, readUrl, writeUrl, type Mode } from './url'

const TITLES: Record<Mode, string> = { learn: 'Learn', explore: 'Explore', research: 'Research', discover: 'Discover' }
const DESKTOP_ONLY: (Mode | null)[] = ['research', 'discover']

/** Phones get Learn and Explore only: a Research/Discover link opens Explore on its target (a time window too, e.g.
 * the asteroid lesson's exposures), or the landing page without one. */
function phoneMode(): Mode | null {
  const u = readUrl()
  const m = u.target !== null || (u.ra !== null && u.dec !== null) ? 'explore' : null
  // fov: the unmounted Research sky map reports a near-zero field while the window narrows
  writeUrl({ mode: m, frame: null, fov: null })
  return m
}

/** Mode switch (URL param `mode`, no router): landing page when absent. */
export default function App() {
  const phone = useIsPhone()
  // checked before the first render, so Research/Discover never start their fields on a phone
  const [redirected, setRedirected] = useState(() => matchMedia(PHONE_QUERY).matches && DESKTOP_ONLY.includes(readUrl().mode))
  const [mode, setModeState] = useState(() => (redirected ? phoneMode() : readUrl().mode))
  const [help, setHelp] = useState(false)
  useEffect(() => {
    const onPop = () => setModeState(readUrl().mode)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  // a desktop window narrowed to phone width, or Back to a Research URL
  useEffect(() => {
    if (phone && DESKTOP_ONLY.includes(mode)) {
      setRedirected(true)
      setModeState(phoneMode())
    }
  }, [phone, mode])
  const setMode = (m: Mode | null) => {
    // a time window is a Research tool: other modes start from the full 16 years
    writeUrl({ mode: m, frame: null, win: null, exposures: null }, true)
    setModeState(m)
    setRedirected(false)
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100 max-md:h-auto max-md:min-h-dvh max-md:pr-[env(safe-area-inset-right)] max-md:pb-[env(safe-area-inset-bottom)] max-md:pl-[env(safe-area-inset-left)]">
      <header className="flex items-center gap-1 border-b border-slate-700 bg-slate-900 px-3 py-1.5 max-md:px-2 max-md:pt-[max(0.375rem,env(safe-area-inset-top))]">
        <button className="mr-3 font-semibold text-sky-300 max-md:mr-1 max-md:min-h-11 max-md:text-sm" onClick={() => setMode(null)}>
          Ultracool Browser
        </button>
        <nav aria-label="Modes" className="flex gap-1">
          {MODES.map((m) => (
            <button
              key={m}
              aria-current={m === mode ? 'page' : undefined}
              className={`rounded px-3 py-1 text-sm max-md:min-h-11 max-md:px-2 ${DESKTOP_ONLY.includes(m) ? 'max-md:hidden' : ''} ${m === mode ? 'bg-sky-700' : 'text-slate-300 hover:bg-slate-800'}`}
              onClick={() => setMode(m)}
            >
              {TITLES[m]}
            </button>
          ))}
        </nav>
        <button className="ml-auto rounded px-3 py-1 text-sm text-slate-300 hover:bg-slate-800 max-md:min-h-11 max-md:px-2" onClick={() => setHelp(true)}>
          ? Help
        </button>
      </header>
      {redirected && <p className="border-b border-slate-700 bg-amber-950/60 px-3 py-2 text-sm text-amber-200 md:hidden">Research and Discover need a larger screen.</p>}
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
