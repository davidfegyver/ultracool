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
}

/** Aladin Lite sky view. Initialised once (StrictMode mounts effects twice); target changes recentre. */
export default function SkyView({ ra, dec, fov, onReady }: Props) {
  const div = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const aladin = useRef<Aladin | null>(null)

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
