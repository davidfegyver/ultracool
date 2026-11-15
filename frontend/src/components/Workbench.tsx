import A, { type Aladin, type Catalog } from 'aladin-lite'
import { useEffect, useRef, useState } from 'react'
import { candidatePeriods, getSummary, ucdsNear, type SeqOptions, type Ucd } from '../api'
import { DEFAULT_TARGET, useFlipbook, useProbe, useSeqResult, useSequence, useTarget, type ProbePoint } from '../hooks'
import { MJD_2018, PIX_ARCSEC, propagate } from '../sky'
import { readUrl, writeUrl } from '../url'
import Catalogs from './Catalogs'
import FoundPanel from './FoundPanel'
import LayersPanel, { Group } from './LayersPanel'
import Player, { ALL_BANDS } from './Player'
import PlotsPanel from './PlotsPanel'
import { ProbeMenu, ProbePanel } from './Probe'
import ResearchPanel from './ResearchPanel'
import SkyView from './SkyView'
import TargetBar from './TargetBar'
import TimeWindow from './TimeWindow'
import UcdSearch from './UcdSearch'

// Explore shows band presets instead of per-band chips, named by time and mission; wavelengths in the hover text.
// The first is the default 16-year story.
const EXPLORE_PRESETS = [
  { label: 'All 16 years', bands: ['W2', 'D6'], title: 'WISE 4.6 µm 2010–2024 + SPHEREx 4.4–5 µm 2025–26' },
  { label: 'WISE 2010–2024', bands: ['W2'], title: '4.6 µm' },
  { label: 'SPHEREx 2025–26', bands: ['D6'], title: '4.4–5.0 µm' },
  { label: 'All colors', bands: ALL_BANDS, title: 'every WISE and SPHEREx band; SPHEREx frames are different wavelengths' },
]

/** Explore (plain findings, expert tools behind "Show advanced") and Research (everything + numbers) share this layout. */
export default function Workbench({ mode }: { mode: 'explore' | 'research' }) {
  const [initialUrl] = useState(readUrl)
  const { resolved, lookup, goTo, busy, error } = useTarget()
  // field size ("Centre field here") and time window (lesson links) from the URL; else the backend's defaults
  const [opts, setOpts] = useState<SeqOptions>(() => ({
    fov_deg: initialUrl.field ?? undefined,
    mjd_min: initialUrl.win?.[0],
    mjd_max: initialUrl.win?.[1],
    wise_exposures: initialUrl.exposures || undefined,
  }))
  const [fb, setFlipbook] = useFlipbook()
  const { seq, error: seqError } = useSequence(resolved, opts, fb.bands)
  const summary = useSeqResult(seq, getSummary)
  const [advanced, setAdvanced] = useState(mode === 'research')
  // name put into the target box from outside (UCD table click); remounts TargetBar with it
  const [picked, setPicked] = useState<string | null>(null)
  const [aladin, setAladin] = useState<Aladin | null>(null)
  const [known, setKnown] = useState<Ucd | null>(null)
  const [skyUcds, setSkyUcds] = useState<Ucd[]>([])
  const [spiffOn, setSpiffOn] = useState(false)
  const [ucdOpen, setUcdOpen] = useState(false)
  const ucdButton = useRef<HTMLButtonElement>(null)
  const ucdDialog = useRef<HTMLDivElement>(null)
  const asteroidCat = useRef<Catalog | null>(null)
  const probe = useProbe(seq)
  const probeCat = useRef<Catalog | null>(null)
  const [tab, setTab] = useState<'target' | 'probe'>('target')
  const hasProbe = !!(probe.point || probe.data)
  const shownTab = hasProbe ? tab : 'target'

  useEffect(() => {
    setKnown(null)
    if (resolved) ucdsNear(resolved).then((r) => setKnown(r[0] ?? null)).catch(() => setKnown(null))
  }, [resolved])

  // a measurement started from the probe menu: show its tab
  useEffect(() => {
    if (probe.busy) setTab('probe')
  }, [probe.busy])

  useEffect(() => {
    if (ucdOpen) ucdDialog.current?.querySelector('input')?.focus()
  }, [ucdOpen])
  const closeUcd = () => {
    setUcdOpen(false)
    ucdButton.current?.focus()
  }

  // known asteroids from the summary as a sky catalog
  // known asteroids only matter when looking at single exposures or a short time window: hidden otherwise
  const timeWindow = opts.mjd_min !== undefined || opts.mjd_max !== undefined || !!opts.wise_exposures
  const asteroids = timeWindow ? summary.data?.asteroids : undefined
  useEffect(() => {
    if (!aladin) return
    if (!asteroidCat.current) {
      asteroidCat.current = A.catalog({ name: 'Known asteroids', color: '#facc15', sourceSize: 14, onClick: 'showTable' })
      aladin.addCatalog(asteroidCat.current)
    }
    asteroidCat.current.removeAll()
    asteroidCat.current.addSources((asteroids ?? []).map((a) => A.source(a.ra, a.dec, { name: a.name, mjd: a.mjd, rate_arcsec_h: a.rate_arcsec_h })))
  }, [aladin, asteroids])

  // probe point on the sky map, at the grid epoch 2018.0 like the flipbook overlay
  const point = probe.point
  useEffect(() => {
    if (!aladin) return
    if (!probeCat.current) {
      probeCat.current = A.catalog({ name: 'Probe', color: '#22d3ee', shape: 'plus', sourceSize: 20 })
      aladin.addCatalog(probeCat.current)
    }
    probeCat.current.removeAll()
    if (point) {
      const at = propagate(point.ra, point.dec, point.pmra_masyr, point.pmdec_masyr, 2000, MJD_2018)
      probeCat.current.addSources([A.source(at.ra, at.dec, { name: 'Probe' })])
    }
  }, [aladin, point])

  /** a different object: back to the default field size, no probe */
  const newTarget = () => {
    setFlipbook({ frameId: null, playing: false })
    setOpts((o) => ({ ...o, fov_deg: undefined }))
    writeUrl({ frame: null, field: null })
    probe.place(null)
  }

  // catalog row: resolve the designation so its (CatWISE) proper motion is kept; unknown names fall back to the row
  const pickUcd = (u: Ucd) => {
    newTarget()
    setUcdOpen(false)
    setPicked(u.designation)
    lookup(u.designation, { name: u.designation, ra: u.ra, dec: u.dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: u.spiff_autotype })
  }
  // new sequence centred on the probe, same field size, with the probe's (mover) proper motion; all in the URL
  const centreOn = (p: ProbePoint) => {
    if (seq) {
      const fov = (seq.grid.width * PIX_ARCSEC) / 3600
      setOpts((o) => ({ ...o, fov_deg: fov }))
      writeUrl({ field: fov.toFixed(6) })
    }
    setFlipbook({ frameId: null, playing: false })
    setPicked(`${p.ra.toFixed(5)} ${p.dec.toFixed(5)}`)
    goTo({ name: null, ...p, epoch_yr: 2000, otype: null, sptype: null })
  }

  return (
    <div className="flex h-full flex-col">
      <TargetBar
        key={picked}
        initial={picked ?? initialUrl.target ?? (initialUrl.ra !== null && initialUrl.dec !== null ? `${initialUrl.ra} ${initialUrl.dec}` : DEFAULT_TARGET)}
        resolved={resolved}
        busy={busy}
        error={error ?? seqError}
        onSubmit={(q) => {
          newTarget()
          lookup(q)
        }}
        badge={
          known && (
            <span className="rounded bg-fuchsia-900 px-2 py-0.5 text-xs">
              Known UCD: {known.spiff_autotype} (SPIFF){known.literature_spectral_type && `, lit. ${known.literature_spectral_type}`}
            </span>
          )
        }
      >
        {advanced && (
          <button
            ref={ucdButton}
            aria-haspopup="dialog"
            aria-expanded={ucdOpen}
            className="rounded bg-fuchsia-900 px-2 py-1 text-xs hover:bg-fuchsia-800"
            onClick={() => setUcdOpen(!ucdOpen)}
          >
            Browse brown dwarfs
          </button>
        )}
        {mode === 'explore' && (
          <label className="ml-2 flex items-center gap-1 text-xs text-slate-300">
            <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} /> Show advanced
          </label>
        )}
      </TargetBar>
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="relative min-h-0 flex-1">
            {resolved && (
              // grid centre = 2018 position, so high-PM stars sit in the middle of the flipbook overlay
              <SkyView
                ra={seq ? Number(seq.grid.wcs.CRVAL1) : resolved.ra}
                dec={seq ? Number(seq.grid.wcs.CRVAL2) : resolved.dec}
                fov={initialUrl.fov ?? 0.25}
                onReady={setAladin}
                minimal={mode === 'explore'}
                onPick={(ra, dec, x, y) => {
                  probe.place({ ra, dec, pmra_masyr: 0, pmdec_masyr: 0 })
                  probe.setMenu({ x, y })
                }}
              />
            )}
            <ProbeMenu probe={probe} onCentre={centreOn} />
            {/* drawer, hidden rather than unmounted so the last search stays */}
            <div
              ref={ucdDialog}
              role="dialog"
              aria-label="Browse brown dwarfs"
              hidden={!ucdOpen}
              className="absolute inset-y-0 right-0 z-20 flex w-[34rem] max-w-full flex-col border-l border-slate-600 bg-slate-900/95 shadow-2xl"
              onKeyDown={(e) => e.key === 'Escape' && closeUcd()}
            >
              <div className="flex items-center border-b border-slate-700 px-2 py-1 text-xs">
                <span className="font-semibold text-slate-300">Brown dwarfs and other ultracool dwarfs (SPIFF catalog)</span>
                <button className="ml-auto rounded bg-slate-700 px-2 py-0.5" aria-label="Close brown dwarf browser" onClick={closeUcd}>
                  ✕
                </button>
              </div>
              <div className="min-h-0 flex-1">
                <UcdSearch
                  onPick={pickUcd}
                  onShowOnSky={(rows) => {
                    setSkyUcds(rows)
                    setSpiffOn(true)
                  }}
                />
              </div>
            </div>
          </div>
          <div className="h-72 shrink-0 border-t border-slate-700 bg-slate-900">
            {/* one plot panel: it follows the Results tab; keys remount it so fold/tab state does not carry over */}
            {shownTab === 'probe' && probe.data ? (
              <PlotsPanel
                key="probe"
                seq={null}
                probe={{ frames: probe.data.frames, spectrum: probe.data.spectrum }}
                periods={candidatePeriods(probe.data.variability)}
                research={mode === 'research'}
              />
            ) : (
              <PlotsPanel key="target" seq={seq} periods={candidatePeriods(summary.data?.variability)} research={mode === 'research'} />
            )}
          </div>
        </div>
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-slate-700 bg-slate-900">
          <Player seq={seq} fb={fb} set={setFlipbook} aladin={aladin} probe={probe} blink presets={mode === 'explore' ? EXPLORE_PRESETS : undefined} />
          <Group title="Results">
            {hasProbe && (
              <div role="tablist" aria-label="Results for" className="flex gap-1 px-2 pt-2 text-xs">
                {(['target', 'probe'] as const).map((t) => (
                  <button
                    key={t}
                    role="tab"
                    id={`results-tab-${t}`}
                    aria-selected={shownTab === t}
                    aria-controls="results-panel"
                    className={`rounded px-3 py-0.5 ${shownTab === t ? (t === 'probe' ? 'bg-cyan-800' : 'bg-sky-700') : 'bg-slate-800 hover:bg-slate-700'}`}
                    onClick={() => setTab(t)}
                  >
                    {t === 'target' ? 'Target' : 'Probe'}
                  </button>
                ))}
              </div>
            )}
            <div id="results-panel" role={hasProbe ? 'tabpanel' : undefined} aria-labelledby={hasProbe ? `results-tab-${shownTab}` : undefined}>
              {shownTab === 'probe' ? (
                <ProbePanel probe={probe} research={mode === 'research'} plots={false} />
              ) : mode === 'explore' ? (
                <FoundPanel summary={summary.data} note={summary.note} busy={summary.busy} />
              ) : (
                <ResearchPanel seq={seq} summary={summary.data} note={summary.note} busy={summary.busy} showAsteroids={timeWindow} />
              )}
            </div>
          </Group>
          {mode === 'research' && (
            <Group title="Fetch exposures for a time window">
              <TimeWindow
                value={opts}
                onApply={(o) => {
                  setFlipbook({ frameId: null, playing: false })
                  setOpts({ ...o, fov_deg: opts.fov_deg })
                  writeUrl({ win: o.mjd_min !== undefined && o.mjd_max !== undefined ? `${o.mjd_min},${o.mjd_max}` : null, exposures: o.wise_exposures ? '1' : null })
                }}
              />
            </Group>
          )}
          <div className={advanced ? '' : 'hidden'}>
            <LayersPanel
              aladin={aladin}
              catalogs={aladin && <Catalogs aladin={aladin} ucds={skyUcds} spiffOn={spiffOn} setSpiffOn={setSpiffOn} />}
            />
          </div>
        </aside>
      </div>
    </div>
  )
}
