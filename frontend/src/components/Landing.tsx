import { useState } from 'react'
import type { Mode } from '../url'
import { GuideLink, TutorialSteps } from './Tutorial'

const TUTORIAL_KEY = 'ultracool-tutorial-dismissed'

const CARDS: { mode: Mode; title: string; who: string; text: string }[] = [
  { mode: 'learn', title: 'Learn', who: 'New to astronomy', text: 'Seven short lessons with real objects: the fastest-moving star in our sky, the coldest brown dwarf, a pulsating giant… each ends with a quick quiz.' },
  { mode: 'explore', title: 'Explore', who: 'Curious minds', text: 'Type any star name or coordinates. Watch 16 years of images and get plain-English answers: does it move, is it cold, does it change?' },
  { mode: 'research', title: 'Research', who: 'Astronomers & students', text: 'Measured proper motion, colors, variability and spectral typing with errors, catalogs and layers, single exposures, CSV export.' },
  { mode: 'discover', title: 'Discover', who: 'Citizen scientists', text: 'Scan a field for everything that moves, see which movers no catalog knows, and classify candidates: real, artifact or unsure.' },
]

export default function Landing({ onMode }: { onMode: (m: Mode) => void }) {
  const [showTutorial, setShowTutorial] = useState(() => !localStorage.getItem(TUTORIAL_KEY))
  const dismiss = () => {
    localStorage.setItem(TUTORIAL_KEY, '1')
    setShowTutorial(false)
  }
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <section>
          <h1 className="text-3xl font-bold text-sky-300">Ultracool Browser</h1>
          <p className="mt-2 max-w-3xl text-lg leading-relaxed text-slate-300">
            Pick any spot in the sky and play 16 years of NASA infrared pictures (WISE 2010, NEOWISE 2014–2024, SPHEREx 2025–2026) like a flipbook. Infrared cameras see
            heat, so cold, dim brown dwarfs, the "failed stars" between planets and stars, show up here although they are nearly invisible to ordinary telescopes. Watch
            things move, change brightness or glow with the colors of a cold world, then measure them.
          </p>
        </section>

        <section aria-labelledby="featured-heading" className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-4">
          <div className="text-xs tracking-wide text-emerald-400 uppercase">Featured result</div>
          <h2 id="featured-heading" className="text-lg font-semibold">
            WISE J2317−6659: the first spectrum-based type for a candidate brown dwarf
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-300">
            This faint infrared source was listed only as a possible brown dwarf, its type (T6) estimated from its brightness. With this app we measured its
            SPHEREx 0.75–5 µm spectrum for the first time: it matches mid-T brown dwarfs (about T6, give or take one subtype), confirming that estimate. It moves
            about 0.5″ per year across 16 years of WISE and SPHEREx images and lies about 30 parsecs (100 light-years) away, consistent with the distance of the
            star pair HD 219509/219495, but it moves about 0.15″ per year differently, so it is not their companion, as Rothermich et al. (2024) had judged likely.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            SPHEREx gives low-resolution spectrophotometry (R ≈ 40–130), not a slit spectrum; the distance (25–40 pc) is estimated from brightness and type.
            "First" means the first we found in catalogues and papers as of November 2026.{' '}
            <a className="underline" href="https://github.com/davidfegyver/ultracool/blob/main/research/verification/J2317_ADVERSARIAL.md" target="_blank" rel="noreferrer">
              Claim-by-claim check
            </a>
            .
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
                className="rounded bg-emerald-800 px-3 py-1 hover:bg-emerald-700"
                href={`?${new URLSearchParams({ mode, target: 'WISE J231728.42-665959.3' })}`}
              >
                {label}
              </a>
            ))}
          </div>
        </section>

        {showTutorial ? (
          <section aria-labelledby="tutorial-heading" className="rounded-lg border border-slate-700 bg-slate-900 p-4">
            <div className="mb-3 flex items-center">
              <h2 id="tutorial-heading" className="text-lg font-semibold">
                How to read a flipbook
              </h2>
              <button className="ml-auto rounded px-2 text-sm text-slate-400 hover:bg-slate-800" onClick={dismiss}>
                Dismiss ✕
              </button>
            </div>
            <TutorialSteps onDone={dismiss} />
          </section>
        ) : (
          <button className="text-sm text-sky-400 underline" onClick={() => setShowTutorial(true)}>
            Show "How to read a flipbook"
          </button>
        )}

        <section aria-label="Choose a mode" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {CARDS.map((c) => (
            <button
              key={c.mode}
              className="flex flex-col rounded-lg border border-slate-700 bg-slate-900 p-4 text-left hover:border-sky-500 hover:bg-slate-800 focus-visible:border-sky-400"
              onClick={() => onMode(c.mode)}
            >
              <span className="text-xs tracking-wide text-slate-400 uppercase">{c.who}</span>
              <span className="text-xl font-semibold text-sky-300">{c.title}</span>
              <span className="mt-1 text-sm leading-relaxed text-slate-300">{c.text}</span>
              <span className="mt-auto pt-3 text-sm text-sky-400">Start →</span>
            </button>
          ))}
        </section>

        <footer className="text-xs text-slate-500">
          Data: NASA/IPAC Infrared Science Archive (WISE, NEOWISE, SPHEREx, CatWISE2020), SIMBAD. Brown-dwarf templates and catalog: SPIFF (Gagné et al. 2026,
          doi:10.5281/zenodo.19051216, CC-BY 4.0). Built for NASA Space Apps 2026. <GuideLink />
        </footer>
      </div>
    </div>
  )
}
