import { useState } from 'react'
import type { Mode } from '../url'
import { GuideLink, TutorialSteps } from './Tutorial'

const TUTORIAL_KEY = 'ultracool-tutorial-dismissed'

const CARDS: { mode: Mode; title: string; who: string; text: string }[] = [
  { mode: 'learn', title: 'Learn', who: 'Start here', text: "Seven short lessons on real objects, like Barnard's Star, a cold brown dwarf and a pulsating giant. Each ends with a quiz." },
  { mode: 'explore', title: 'Explore', who: 'Look something up', text: 'Type a star name or coordinates. You get the flipbook and short answers: is it moving, is it cold, is it changing?' },
  { mode: 'research', title: 'Research', who: 'For astronomers', text: 'The numbers behind those answers, with error bars: motion, colours, variability, spectral type. Plus catalogue overlays, single frames and CSV export.' },
  { mode: 'discover', title: 'Discover', who: 'Hunt for new ones', text: "Find everything that moves in a patch of sky, check it against known catalogues, and decide what's real." },
]

export default function Landing({ onMode }: { onMode: (m: Mode) => void }) {
  const [showTutorial, setShowTutorial] = useState(() => !localStorage.getItem(TUTORIAL_KEY))
  const dismiss = () => {
    localStorage.setItem(TUTORIAL_KEY, '1')
    setShowTutorial(false)
  }
  return (
    <div className="h-full overflow-y-auto">
      {/* phones: Learn/Explore cards right after the featured result, tutorial below them */}
      <div className="mx-auto max-w-5xl space-y-6 p-6 max-md:flex max-md:flex-col max-md:gap-6 max-md:space-y-0 max-md:p-4">
        <section>
          <h1 className="text-3xl font-bold text-sky-300">Ultracool Browser</h1>
          <p className="mt-2 max-w-3xl text-lg leading-relaxed text-slate-300">
            Type a star name or coordinates and flip through 16 years of NASA infrared images of that spot: WISE (2010), NEOWISE (2014–2024) and SPHEREx (2025–2026).
            Brown dwarfs are too cold to see well with ordinary telescopes, but they show up in infrared, and the nearby ones visibly move from one image to the next.
          </p>
        </section>

        <section aria-labelledby="featured-heading" className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-4">
          <div className="text-xs tracking-wide text-emerald-400 uppercase">What we found</div>
          <h2 id="featured-heading" className="text-lg font-semibold">
            Our first result: a spectral type for WISE J2317−6659
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-300">
            Rothermich et al. (2024) listed this faint source as a probable T6 brown dwarf, based on its brightness alone. We measured its SPHEREx spectrum with this app,
            and it agrees: about T6, give or take one subtype. It's roughly 30 parsecs (100 light-years) away and moves half an arcsecond a year, but not together with
            the star pair HD 219509/219495 next to it, so it's a lone brown dwarf rather than their companion.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Fine print: SPHEREx spectra are low resolution (R ≈ 40–130), and the distance (25–40 pc) comes from brightness and type, not a parallax. We found no earlier
            spectrum in catalogues or papers as of November 2026.{' '}
            <a className="underline" href="https://github.com/davidfegyver/ultracool/blob/main/docs/results.md#wise-j2317-6659-gets-a-spectrum-based-type" target="_blank" rel="noreferrer">
              How we checked this →
            </a>
          </p>
          <div className="mt-3 flex gap-2 text-sm">
            {(
              [
                ['explore', 'See it in Explore'],
                ['research', 'See the measurements'],
              ] as const
            ).map(([mode, label]) => (
              <a
                key={mode}
                className={`rounded bg-emerald-800 px-3 py-1 hover:bg-emerald-700 ${mode === 'research' ? 'max-md:hidden' : 'max-md:inline-flex max-md:min-h-11 max-md:items-center'}`}
                href={`?${new URLSearchParams({ mode, target: 'WISE J231728.42-665959.3' })}`}
              >
                {label}
              </a>
            ))}
          </div>
        </section>

        {showTutorial ? (
          <section aria-labelledby="tutorial-heading" className="rounded-lg border border-slate-700 bg-slate-900 p-4 max-md:order-1">
            <div className="mb-3 flex items-center">
              <h2 id="tutorial-heading" className="text-lg font-semibold">
                How to read a flipbook
              </h2>
              <button className="ml-auto rounded px-2 text-sm text-slate-400 hover:bg-slate-800 max-md:min-h-11" onClick={dismiss}>
                Hide
              </button>
            </div>
            <TutorialSteps onDone={dismiss} />
          </section>
        ) : (
          <button className="text-sm text-sky-400 underline max-md:order-1 max-md:min-h-11 max-md:self-start" onClick={() => setShowTutorial(true)}>
            How do I read a flipbook?
          </button>
        )}

        <section aria-label="Choose a mode" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {CARDS.map((c) => (
            <button
              key={c.mode}
              className={`flex flex-col rounded-lg border border-slate-700 bg-slate-900 p-4 text-left hover:border-sky-500 hover:bg-slate-800 focus-visible:border-sky-400 ${c.mode === 'research' || c.mode === 'discover' ? 'max-md:hidden' : ''}`}
              onClick={() => onMode(c.mode)}
            >
              <span className="text-xs tracking-wide text-slate-400 uppercase">{c.who}</span>
              <span className="text-xl font-semibold text-sky-300">{c.title}</span>
              <span className="mt-1 text-sm leading-relaxed text-slate-300">{c.text}</span>
              <span className="mt-auto pt-3 text-sm text-sky-400">Open →</span>
            </button>
          ))}
        </section>

        <footer className="text-xs text-slate-500 max-md:order-2">
          Data: NASA/IPAC Infrared Science Archive (WISE, NEOWISE, SPHEREx, CatWISE2020), SIMBAD. Brown-dwarf templates and catalog: SPIFF (Gagné et al. 2026,
          doi:10.5281/zenodo.19051216, CC-BY 4.0). Built for NASA Space Apps 2026. <GuideLink />
        </footer>
      </div>
    </div>
  )
}
