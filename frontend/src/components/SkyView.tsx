import A, { type Aladin } from 'aladin-lite'
import { useEffect, useRef } from 'react'
import { writeUrl } from '../url'

// IRSA mirrors of CDS HiPS: used when available so the sky still renders while CDS is down (seen Nov 2026)
const IRSA = 'https://irsa.ipac.caltech.edu/data/hips/CDS'
export const HIPS_URL: Record<string, string> = {
  'CDS/P/allWISE/color': `${IRSA}/AllWISE/RGB-W4-W2-W1`,
  'CDS/P/allWISE/W1': `${IRSA}/AllWISE/W1`,
  'CDS/P/allWISE/W2': `${IRSA}/AllWISE/W2`,
  'CDS/P/allWISE/W3': `${IRSA}/AllWISE/W3`,
  'CDS/P/allWISE/W4': `${IRSA}/AllWISE/W4`,
  'CDS/P/DSS2/color': `${IRSA}/DSS2/color`,
}
export const DEFAULT_BASE = 'CDS/P/allWISE/color'

type Props = {
  ra: number
  dec: number
  fov: number
  onReady: (a: Aladin) => void
  /** right-click (without dragging: right-drag is Aladin's contrast control) or touch long-press: sky position and
   * client px. Left-drag panning never calls it. */
  onPick?: (ra: number, dec: number, clientX: number, clientY: number) => void
}

/** Aladin Lite sky view. Initialised once (StrictMode mounts effects twice); target changes recentre. */
export default function SkyView({ ra, dec, fov, onReady, onPick }: Props) {
  const div = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const aladin = useRef<Aladin | null>(null)
  const pickRef = useRef(onPick)
  pickRef.current = onPick

  useEffect(() => {
    if (started.current) return
    started.current = true
    A.init.then(() => {
      const a = A.aladin(div.current!, {
        survey: HIPS_URL[DEFAULT_BASE],
        fov,
        target: `${ra} ${dec}`,
        projection: 'TAN',
        cooFrame: 'ICRS',
        showReticle: true,
        showLayersControl: false,
      })
      a.on('zoomChanged', (f) => writeUrl({ fov: Number(f).toFixed(4) }))
      const el = div.current!
      const pick = (e: MouseEvent) => {
        const r = el.getBoundingClientRect()
        let at: [number, number] | undefined
        try {
          at = a.pix2world(e.clientX - r.left, e.clientY - r.top)
        } catch {
          return // off the projection
        }
        if (at && Number.isFinite(at[0]) && Number.isFinite(at[1])) pickRef.current?.(at[0], at[1], e.clientX, e.clientY)
      }
      // capture phase: runs before Aladin's canvas handlers
      let down: [number, number] | null = null
      el.addEventListener('mousedown', (e) => (down = e.button === 2 ? [e.clientX, e.clientY] : null), true)
      el.addEventListener('mouseup', (e) => {
        if (e.button === 2 && down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 5) pick(e)
        down = null
      }, true)
      el.addEventListener('contextmenu', (e) => {
        e.preventDefault()
        if ((e as PointerEvent).pointerType === 'touch') pick(e)
      }, true)
      aladin.current = a
      onReady(a)
    })
    // init exactly once; later prop changes are handled below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    aladin.current?.gotoRaDec(ra, dec)
  }, [ra, dec])

  return <div ref={div} className="h-full w-full" />
}
