import { useEffect, useRef, useState, type ReactNode } from 'react'

const Frame = ({ x = 0, y = 0, children }: { x?: number; y?: number; children?: ReactNode }) => (
  <g transform={`translate(${x} ${y})`}>
    <rect width={60} height={60} fill="#020617" stroke="#475569" />
    <circle cx={12} cy={14} r={1.5} fill="#cbd5e1" />
    <circle cx={46} cy={40} r={2} fill="#cbd5e1" />
    <circle cx={20} cy={48} r={1} fill="#cbd5e1" />
    {children}
  </g>
)
const Label = ({ x, y, children }: { x: number; y: number; children: ReactNode }) => (
  <text x={x} y={y} fill="#94a3b8" fontSize={8} textAnchor="middle">
    {children}
  </text>
)

const STEPS: { title: string; text: string; art: ReactNode }[] = [
  {
    title: 'What is a flipbook?',
    text: 'A flipbook is a stack of infrared images of one small patch of sky, taken between 2010 and 2026 by WISE, NEOWISE and SPHEREx and lined up pixel by pixel.',
    art: (
      <>
        <Frame x={10} y={14} />
        <Frame x={30} y={8} />
        <Frame x={50} y={2} />
        <Label x={40} y={84}>2010</Label>
        <Label x={80} y={84}>2026</Label>
      </>
    ),
  },
  {
    title: 'Look for things that move',
    text: 'Press play. Faraway stars stay still, a nearby star or brown dwarf drifts slowly, and an asteroid shoots across within a day.',
    art: (
      <Frame x={30} y={10}>
        {[0, 1, 2].map((i) => <circle key={i} cx={18 + i * 12} cy={36 - i * 8} r={2.5} fill="#f8fafc" opacity={0.35 + i * 0.3} />)}
        <path d="M18 36 L42 20" stroke="#38bdf8" strokeDasharray="2 2" />
      </Frame>
    ),
  },
  {
    title: 'Predicted position',
    text: 'The pink circle is where the catalogues say your object should be on that date. If the dot stays inside it, the object moves as expected.',
    art: (
      <Frame x={30} y={10}>
        <circle cx={30} cy={30} r={3} fill="#f8fafc" />
        <circle cx={30} cy={30} r={8} fill="none" stroke="#f472b6" strokeWidth={1.5} />
      </Frame>
    ),
  },
  {
    title: 'Select and measure',
    text: 'To measure another source, drag the cyan crosshair onto it or right-click it on the sky map, then choose "Measure this source". The circle shows the area we measure.',
    art: (
      <Frame x={30} y={10}>
        <circle cx={22} cy={36} r={3} fill="#f8fafc" />
        <circle cx={22} cy={36} r={7} fill="none" stroke="#22d3ee" strokeWidth={1.5} />
        <path d="M22 26v6M22 40v6M12 36h6M26 36h6" stroke="#22d3ee" strokeWidth={1.5} />
      </Frame>
    ),
  },
  {
    title: 'W1 and W2',
    text: 'Ordinary stars look about the same in W1 (3.4 µm) and W2 (4.6 µm). Cold brown dwarfs are much brighter in W2, so a dot that only shows up in W2 is worth a closer look.',
    art: (
      <>
        <Frame x={6}>
          <circle cx={30} cy={30} r={1} fill="#64748b" />
        </Frame>
        <Frame x={74}>
          <circle cx={30} cy={30} r={3.5} fill="#f8fafc" />
        </Frame>
        <Label x={36} y={72}>W1</Label>
        <Label x={104} y={72}>W2</Label>
      </>
    ),
  },
  {
    title: 'The light curve',
    text: "We set the contrast of each image separately, so you can't judge brightness by eye. Use the light curve plot instead: smooth repeating waves mean the star pulsates, sudden jumps mean dust or flares.",
    art: (
      <g transform="translate(10 10)">
        <path d="M0 60 H120 M0 60 V0" stroke="#475569" />
        <path d="M0 30 Q15 5 30 30 T60 30 T90 30 T120 30" fill="none" stroke="#38bdf8" />
        {[8, 26, 44, 62, 80, 98, 114].map((x, i) => <circle key={x} cx={x} cy={[16, 26, 40, 22, 38, 20, 34][i]} r={2} fill="#f472b6" />)}
      </g>
    ),
  },
  {
    title: 'Phantom objects',
    text: "Cameras create fake sources too: spikes and rings around bright stars, afterimages, cosmic-ray hits. If something appears on only one date or in only one band, it's probably one of those. Real objects show up again.",
    art: (
      <Frame x={30} y={10}>
        <circle cx={26} cy={28} r={3} fill="#f8fafc" />
        <path d="M26 14 V42 M12 28 H40" stroke="#f8fafc" strokeWidth={0.6} />
        <circle cx={44} cy={44} r={6} fill="none" stroke="#94a3b8" strokeWidth={0.8} opacity={0.6} />
      </Frame>
    ),
  },
]

/** "How to read a flipbook": a short illustrated stepper. */
export function TutorialSteps({ onDone }: { onDone?: () => void }) {
  const [i, setI] = useState(0)
  const s = STEPS[i]
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <svg viewBox="0 0 140 90" role="img" aria-label={s.title} className="h-36 w-56 shrink-0 rounded bg-slate-950 max-md:self-center">
        {s.art}
      </svg>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="text-xs text-slate-400">
          Step {i + 1} of {STEPS.length}
        </div>
        <h3 className="font-semibold">{s.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-300">{s.text}</p>
        <div className="mt-auto flex gap-2 pt-2">
          <button className="rounded bg-slate-700 px-3 py-1 text-sm disabled:opacity-40 max-md:min-h-11" disabled={i === 0} onClick={() => setI(i - 1)}>
            ← Back
          </button>
          {i < STEPS.length - 1 ? (
            <button className="rounded bg-sky-700 px-3 py-1 text-sm hover:bg-sky-600 max-md:min-h-11" onClick={() => setI(i + 1)}>
              Next →
            </button>
          ) : (
            onDone && (
              <button className="rounded bg-emerald-700 px-3 py-1 text-sm hover:bg-emerald-600 max-md:min-h-11" onClick={onDone}>
                Got it
              </button>
            )
          )}
        </div>
      </div>
    </div>
  )
}

const GUIDE_URL = 'https://github.com/davidfegyver/ultracool/blob/main/docs/user-guide.md'

/** "Read the full guide" (new tab) */
export function GuideLink({ className = '' }: { className?: string }) {
  return (
    // relative: keeps the absolutely positioned sr-only text inside the scrolling page instead of stretching the document
    <a className={`relative text-sky-400 underline ${className}`} href={GUIDE_URL} target="_blank" rel="noreferrer">
      Read the full guide<span className="sr-only"> (opens in a new tab)</span> ↗
    </a>
  )
}

/** The tutorial as a modal (Help button). Native <dialog>: focus trap and Esc come for free. */
export default function TutorialDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (open) ref.current?.showModal()
    else ref.current?.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="tutorial-title"
      className="m-auto w-[44rem] max-w-[95vw] rounded-lg border border-slate-600 bg-slate-900 p-4 text-slate-100 backdrop:bg-black/60"
    >
      <div className="mb-3 flex items-center max-md:flex-wrap">
        <h2 id="tutorial-title" className="text-lg font-semibold">
          How to read a flipbook
        </h2>
        {/* phones: ✕ stays on the title row, the guide link wraps below */}
        <GuideLink className="ml-auto text-sm max-md:order-last max-md:ml-0 max-md:basis-full" />
        <button className="ml-2 rounded px-2 text-slate-400 hover:bg-slate-800 max-md:ml-auto max-md:min-h-11 max-md:min-w-11" aria-label="Close tutorial" onClick={onClose}>
          ✕
        </button>
      </div>
      {open && <TutorialSteps onDone={onClose} />}
    </dialog>
  )
}
