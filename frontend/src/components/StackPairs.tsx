import { useState } from 'react'
import type { Resolved, Sequence } from '../api'
import { mjdToIso, propagate, worldToPx } from '../sky'
import { Marks } from './Player'

const BANDS = ['W1', 'W2'] as const

/** W1 and W2 deep stacks of the same MJD window side by side (color lesson), with the PM-predicted circle at mid-window. */
export default function StackPairs({ seq, windows, target }: { seq: Sequence | null; windows: [number, number][]; target: Resolved }) {
  const [w, setW] = useState(0)
  // stacks are cached by URL: request them only once every frame is in
  if (!seq || seq.status !== 'done')
    return <p className="p-4 text-xs text-slate-400">{seq?.status === 'error' ? seq.error : `Collecting pictures… ${seq ? `${seq.done}/${seq.total}` : ''}`}</p>
  const [lo, hi] = windows[w]
  const p = propagate(target.ra, target.dec, target.pmra_masyr, target.pmdec_masyr, target.epoch_yr, (lo + hi) / 2)
  const [x, y] = worldToPx(seq.grid.wcs, seq.grid.height, p.ra, p.dec)
  const years = (m: number) => mjdToIso(m).slice(0, 4)
  return (
    <div className="space-y-2 p-2 text-xs">
      <div role="group" aria-label="Time window" className="flex flex-wrap items-center justify-center gap-1">
        <span className="text-slate-400">Deep stack of</span>
        {windows.map(([a, b], i) => (
          <button key={a} aria-pressed={i === w} className={`rounded px-2 py-0.5 max-md:min-h-11 ${i === w ? 'bg-sky-700' : 'bg-slate-800 hover:bg-slate-700'}`} onClick={() => setW(i)}>
            {years(a)}–{years(b)}
          </button>
        ))}
      </div>
      <div className="flex justify-center gap-3">
        {BANDS.map((b) => (
          // phones: the two stacks share the width, side by side
          <figure key={b} className="text-center max-md:min-w-0 max-md:flex-1">
            <svg role="img" aria-label={`${b} deep stack ${years(lo)}–${years(hi)}`} viewBox={`0 0 ${seq.grid.width} ${seq.grid.height}`} className="h-[260px] w-[260px] bg-black max-md:aspect-square max-md:h-auto max-md:w-full">
              <image
                href={`/api/sequences/${seq.id}/stack.png?band=${b}&mjd_min=${lo}&mjd_max=${hi}`}
                width={seq.grid.width}
                height={seq.grid.height}
                preserveAspectRatio="none"
                style={{ imageRendering: 'pixelated' }}
              />
              <Marks marks={[{ x, y }]} width={seq.grid.width} />
            </svg>
            <figcaption className="mt-1">
              {b} ({b === 'W1' ? '3.4' : '4.6'} µm)
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  )
}
