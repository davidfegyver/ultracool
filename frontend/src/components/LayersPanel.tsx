import type { Aladin, ImageLayer } from 'aladin-lite'
import { useRef, useState, type ReactNode } from 'react'
import { DEFAULT_BASE, HIPS_URL } from './SkyView'

const OVERLAYS = [
  ...[1, 2, 3, 4, 5, 6].map((i) => `CDS/P/SPHEREx/QR2/D${i}`),
  'CDS/P/unWISE/W1',
  'CDS/P/unWISE/W2',
  'CDS/P/NEOWISER/W1',
  'CDS/P/NEOWISER/W2',
  ...[1, 2, 3, 4].map((i) => `CDS/P/allWISE/W${i}`),
]
const BASES = [DEFAULT_BASE, 'CDS/P/unWISE/color-W2-W1W2-W1', 'CDS/P/SPHEREx/QR2/color', 'CDS/P/DSS2/color']

export function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-slate-700">
      <h3 className="bg-slate-800 px-2 py-1 text-xs font-semibold tracking-wide text-slate-300 uppercase">{title}</h3>
      <div>{children}</div>
    </section>
  )
}

/** Eye toggle + label + optional opacity slider: one row of the layers panel. */
export function LayerRow(props: {
  label: ReactNode
  on: boolean
  onToggle: () => void
  opacity?: number
  onOpacity?: (o: number) => void
  selected?: boolean
  onClick?: () => void
  children?: ReactNode
  rowRef?: (el: HTMLDivElement | null) => void
}) {
  return (
    <div
      ref={props.rowRef}
      className={`flex items-center gap-2 px-2 py-1 text-xs ${props.selected ? 'bg-sky-900' : 'hover:bg-slate-800'} ${props.onClick ? 'cursor-pointer' : ''}`}
      onClick={props.onClick}
    >
      <button
        aria-label={props.on ? 'Hide layer' : 'Show layer'}
        aria-pressed={props.on}
        className={`w-5 shrink-0 text-base ${props.on ? 'text-sky-300' : 'text-slate-600'}`}
        onClick={(e) => {
          e.stopPropagation()
          props.onToggle()
        }}
      >
        {props.on ? '●' : '○'}
      </button>
      <div className="min-w-0 flex-1 truncate">{props.label}</div>
      {props.onOpacity && (
        <input
          aria-label="Opacity"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={props.opacity}
          className="w-20"
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => props.onOpacity!(Number(e.target.value))}
        />
      )}
      {props.children}
    </div>
  )
}

function OverlayRow({ aladin, id }: { aladin: Aladin; id: string }) {
  const [on, setOn] = useState(false)
  const [opacity, setOpacity] = useState(0.6)
  const layer = useRef<ImageLayer | null>(null)
  const apply = (nextOn: boolean, o: number) => {
    if (nextOn && !layer.current) {
      layer.current = aladin.newImageSurvey(HIPS_URL[id] ?? id)
      aladin.setOverlayImageLayer(layer.current, id)
    }
    layer.current?.setOpacity(nextOn ? o : 0)
  }
  return (
    <LayerRow
      label={id.replace('CDS/P/', '')}
      on={on}
      onToggle={() => {
        setOn(!on)
        apply(!on, opacity)
      }}
      opacity={opacity}
      onOpacity={(o) => {
        setOpacity(o)
        apply(on, o)
      }}
    />
  )
}

type Props = {
  aladin: Aladin | null
  frames: ReactNode
  catalogs?: ReactNode
  extraOverlays?: ReactNode
}

export default function LayersPanel({ aladin, frames, catalogs, extraOverlays }: Props) {
  const [base, setBase] = useState(DEFAULT_BASE)
  return (
    <div className="text-slate-200">
      <Group title="Flipbook frames">{frames}</Group>
      {catalogs && <Group title="Catalogs">{catalogs}</Group>}
      {aladin && (
        <>
          <Group title="Survey overlays">
            {extraOverlays}
            {OVERLAYS.map((id) => (
              <OverlayRow key={id} aladin={aladin} id={id} />
            ))}
          </Group>
          <Group title="Base">
            {BASES.map((id) => (
              <label key={id} className="flex items-center gap-2 px-2 py-1 text-xs hover:bg-slate-800">
                <input
                  type="radio"
                  name="base"
                  checked={base === id}
                  onChange={() => {
                    setBase(id)
                    aladin.setBaseImageLayer(HIPS_URL[id] ?? id)
                  }}
                />
                {id.replace('CDS/P/', '')}
              </label>
            ))}
          </Group>
        </>
      )}
    </div>
  )
}
