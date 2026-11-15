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
    title: 'One patch of sky, many dates',
    text: 'A flipbook is a pile of infrared pictures of the same small patch of sky, taken between 2010 and 2026 by WISE, NEOWISE and SPHEREx, lined up pixel by pixel.',
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
    title: 'Press play, watch for movement',
    text: 'Pictures play oldest first. Distant stars stay frozen. A dot that slides steadily is a nearby star or brown dwarf; one that jumps around in a single day is an asteroid.',
    art: (
      <Frame x={30} y={10}>
        {[0, 1, 2].map((i) => <circle key={i} cx={18 + i * 12} cy={36 - i * 8} r={2.5} fill="#f8fafc" opacity={0.35 + i * 0.3} />)}
        <path d="M18 36 L42 20" stroke="#38bdf8" strokeDasharray="2 2" />
      </Frame>
    ),
  },
  {
    title: 'The pink circle',
    text: 'The pink circle shows where catalogs predict your object on that date. If the dot sits in the circle on every date, the object is moving just as expected.',
    art: (
      <Frame x={30} y={10}>
        <circle cx={30} cy={30} r={3} fill="#f8fafc" />
        <circle cx={30} cy={30} r={8} fill="none" stroke="#f472b6" strokeWidth={1.5} />
      </Frame>
    ),
  },
  {
    title: 'The cyan probe',
    text: 'Something else caught your eye? Drag the cyan crosshair onto it, or right-click the sky map. Its circle is the measuring aperture. Nothing is measured until you pick "Measure this source" in the menu that opens.',
    art: (
      <Frame x={30} y={10}>
        <circle cx={22} cy={36} r={3} fill="#f8fafc" />
        <circle cx={22} cy={36} r={7} fill="none" stroke="#22d3ee" strokeWidth={1.5} />
        <path d="M22 26v6M22 40v6M12 36h6M26 36h6" stroke="#22d3ee" strokeWidth={1.5} />
      </Frame>
    ),
  },
  {
    title: 'Two infrared colors',
    text: 'W1 (3.4 µm) and W2 (4.6 µm) are two infrared "colors". Ordinary stars look about the same in both. Cold brown dwarfs are much brighter in W2, so a dot that appears only in W2 is exciting.',
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
    title: 'Brightness lives in the light curve',
    text: 'Each picture has its contrast adjusted on its own, so brightness changes hide in the images. The light curve plot shows brightness against time: regular waves mean pulsation, random jumps mean dust or flares.',
    art: (
      <g transform="translate(10 10)">
        <path d="M0 60 H120 M0 60 V0" stroke="#475569" />
        <path d="M0 30 Q15 5 30 30 T60 30 T90 30 T120 30" fill="none" stroke="#38bdf8" />
        {[8, 26, 44, 62, 80, 98, 114].map((x, i) => <circle key={x} cx={x} cy={[16, 26, 40, 22, 38, 20, 34][i]} r={2} fill="#f472b6" />)}
      </g>
    ),
  },
  {
    title: 'Real or ghost?',
    text: 'Cameras make fake objects: spikes and rings around bright stars, afterimages, cosmic-ray hits. Something seen on only one date or in only one band is usually an artifact. Real objects come back.',
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
      <svg viewBox="0 0 140 90" role="img" aria-label={s.title} className="h-36 w-56 shrink-0 rounded bg-slate-950">
        {s.art}
      </svg>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="text-xs text-slate-400">
          Step {i + 1} of {STEPS.length}
        </div>
        <h3 className="font-semibold">{s.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-300">{s.text}</p>
        <div className="mt-auto flex gap-2 pt-2">
          <button className="rounded bg-slate-700 px-3 py-1 text-sm disabled:opacity-40" disabled={i === 0} onClick={() => setI(i - 1)}>
            ← Back
          </button>
          {i < STEPS.length - 1 ? (
            <button className="rounded bg-sky-700 px-3 py-1 text-sm hover:bg-sky-600" onClick={() => setI(i + 1)}>
              Next →
            </button>
          ) : (
            onDone && (
              <button className="rounded bg-emerald-700 px-3 py-1 text-sm hover:bg-emerald-600" onClick={onDone}>
                Got it
              </button>
            )
          )}
        </div>
      </div>
    </div>
  )
}

const GUIDE_URL = 'https://github.com/davidfegyver/ultracool/blob/main/docs/GUIDE.md'

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
      <div className="mb-3 flex items-center">
        <h2 id="tutorial-title" className="text-lg font-semibold">
          How to read a flipbook
        </h2>
        <GuideLink className="ml-auto text-sm" />
        <button className="ml-2 rounded px-2 text-slate-400 hover:bg-slate-800" aria-label="Close tutorial" onClick={onClose}>
          ✕
        </button>
      </div>
      {open && <TutorialSteps onDone={onClose} />}
    </dialog>
  )
}
