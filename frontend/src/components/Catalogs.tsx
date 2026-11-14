import A, { type Aladin, type Catalog } from 'aladin-lite'
import { useEffect, useRef, useState } from 'react'
import { searchUcds, type Ucd } from '../api'
import { LayerRow } from './LayersPanel'

// Harvard mirrors of VizieR/SIMBAD: vizier.unistra.fr and simbad.cds were unreachable (Nov 2026); both send CORS *
const vizier = (src: string, t: string, r: number) =>
  `https://vizier.cfa.harvard.edu/viz-bin/votable?-source=${src}&-c=${encodeURIComponent(t)}&-c.rd=${r}&-out.max=10000`
const simbad = (t: string, r: number) => {
  const [ra, dec] = t.split(' ')
  const adql = `SELECT TOP 10000 main_id, ra, dec, otype, sp_type, pmra, pmdec FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', ${ra}, ${dec}, ${r}))=1`
  return `https://simbad.harvard.edu/simbad/sim-tap/sync?request=doQuery&lang=adql&format=votable/td&query=${encodeURIComponent(adql)}`
}

type Spec = { name: string; make: (target: string, r: number) => Catalog }
const SPECS: Spec[] = [
  { name: 'Gaia DR3', make: (t, r) => A.catalogFromURL(vizier('I/355/gaiadr3', t, r), { name: 'Gaia DR3', onClick: 'showTable' }) },
  { name: 'CatWISE2020', make: (t, r) => A.catalogFromURL(vizier('II/365/catwise', t, r), { name: 'CatWISE2020', onClick: 'showTable' }) },
  { name: 'SIMBAD', make: (t, r) => A.catalogFromURL(simbad(t, r), { name: 'SIMBAD', onClick: 'showTable' }) },
]
/** Remote catalogs: queried around the current view centre the first time the eye is turned on. */
function RemoteRow({ aladin, spec, onVisible }: { aladin: Aladin; spec: Spec; onVisible: (on: boolean) => void }) {
  const [on, setOn] = useState(false)
  const cat = useRef<Catalog | null>(null)
  return (
    <LayerRow
      label={spec.name}
      on={on}
      onToggle={() => {
        if (!on && !cat.current) {
          const [ra, dec] = aladin.getRaDec()
          cat.current = spec.make(`${ra} ${dec}`, Math.min(aladin.getFov()[0] / 2, 0.5))
          aladin.addCatalog(cat.current)
        } else if (on) cat.current?.hide()
        else cat.current?.show()
        setOn(!on)
        onVisible(!on)
      }}
    />
  )
}

type Props = {
  aladin: Aladin
  /** UCDs to plot in the "SPIFF UCDs" layer; empty = load the whole catalog (first 5000) on eye-on. */
  ucds: Ucd[]
  spiffOn: boolean
  setSpiffOn: (on: boolean) => void
  /** number of visible catalog layers (rectangle select needs at least one) */
  onVisibleCount: (n: number) => void
}

export default function Catalogs({ aladin, ucds, spiffOn, setSpiffOn, onVisibleCount }: Props) {
  const visible = useRef(new Set<string>())
  const spiff = useRef<Catalog | null>(null)
  const report = (name: string, on: boolean) => {
    if (on) visible.current.add(name)
    else visible.current.delete(name)
    onVisibleCount(visible.current.size)
  }

  useEffect(() => {
    if (!spiffOn) {
      spiff.current?.hide()
      report('SPIFF UCDs', false)
      return
    }
    if (!spiff.current) {
      spiff.current = A.catalog({ name: 'SPIFF UCDs', color: '#f472b6', sourceSize: 12, onClick: 'showTable' })
      aladin.addCatalog(spiff.current)
    }
    const cat = spiff.current
    let stale = false
    ;(ucds.length ? Promise.resolve(ucds) : searchUcds({ limit: 5000 })).then((rows) => {
      if (stale) return
      cat.removeAll()
      cat.addSources(rows.map((u) => A.source(u.ra, u.dec, { designation: u.designation, spt: u.spiff_autotype, lit_spt: u.literature_spectral_type ?? '' })))
      cat.show()
    })
    report('SPIFF UCDs', true)
    return () => {
      stale = true
    }
  }, [spiffOn, ucds]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {SPECS.map((s) => (
        <RemoteRow key={s.name} aladin={aladin} spec={s} onVisible={(on) => report(s.name, on)} />
      ))}
      <LayerRow label="SPIFF UCDs" on={spiffOn} onToggle={() => setSpiffOn(!spiffOn)} />
    </>
  )
}
