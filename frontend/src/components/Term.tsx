import { useId, useState, type ReactNode } from 'react'

const GLOSSARY = {
  'proper motion': 'How fast a star slides across the sky, in arcseconds per year. Only nearby objects move enough to see.',
  'W1−W2': 'Brightness difference between WISE infrared bands W1 (3.4 µm) and W2 (4.6 µm), in magnitudes. Big positive values mean a very cold object.',
  spectrum: 'Brightness at many wavelengths (colors). Molecules like water and methane carve dips into it, which tells us how cold an object is.',
  'light curve': 'Brightness plotted against time.',
  'brown dwarf': 'An object between a planet and a star: too small to burn hydrogen, so it slowly cools and glows mostly in infrared.',
  'deep stack': 'Several pictures from the same period added together, so faint objects rise above the noise.',
  artifact: 'Something in a picture that is not really in the sky: a reflection (ghost), an afterimage on the detector (latent), a spike around a bright star, or a cosmic-ray hit.',
  arcsecond: '1/3600 of a degree. The full Moon is about 1800 arcseconds wide.',
  period: 'The time it takes a repeating brightness change to come back to the same point.',
  sigma: 'How many times bigger a measurement is than its uncertainty. Above about 5 sigma it is very unlikely to be noise.',
} as const
export type GlossaryTerm = keyof typeof GLOSSARY

/** Jargon word with a hover/focus explanation. The tooltip is `position: fixed` at the word, so it never widens a
 * scrolling panel (an absolute one made the sidebar scroll sideways). */
export default function Term({ k, children }: { k: GlossaryTerm; children?: ReactNode }) {
  const id = useId()
  const [at, setAt] = useState<{ left: number; top: number } | null>(null)
  const show = (e: React.SyntheticEvent<HTMLSpanElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    setAt({ left: Math.max(8, Math.min(r.left, innerWidth - 264)), top: r.top - 4 })
  }
  const hide = () => setAt(null)
  return (
    <span
      tabIndex={0}
      aria-describedby={id}
      className="cursor-help underline decoration-dotted underline-offset-2 focus:outline-none focus-visible:ring-1 focus-visible:ring-sky-400"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onKeyDown={(e) => e.key === 'Escape' && hide()}
    >
      {children ?? k}
      <span
        id={id}
        role="tooltip"
        hidden={!at}
        className="fixed z-50 w-64 -translate-y-full rounded bg-slate-700 p-2 text-xs font-normal text-slate-100 normal-case no-underline shadow-lg"
        style={at ?? undefined}
      >
        {GLOSSARY[k]}
      </span>
    </span>
  )
}
