import type { ReactNode } from 'react'

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

/** Jargon word with a hover/focus explanation. */
export default function Term({ k, children }: { k: GlossaryTerm; children?: ReactNode }) {
  return (
    <span tabIndex={0} className="group relative cursor-help underline decoration-dotted underline-offset-2 focus:outline-none focus-visible:ring-1 focus-visible:ring-sky-400">
      {children ?? k}
      <span
        role="tooltip"
        className="invisible absolute bottom-full left-0 z-30 mb-1 w-64 rounded bg-slate-700 p-2 text-xs font-normal text-slate-100 normal-case no-underline shadow-lg group-hover:visible group-focus:visible"
      >
        {GLOSSARY[k]}
      </span>
    </span>
  )
}
