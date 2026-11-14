import A, { type Aladin, type Catalog, type Source } from 'aladin-lite'
import { useCallback, useEffect, useRef, useState } from 'react'
import { candidatePeriods, getSummary, ucdsNear, type SeqOptions, type Ucd } from '../api'
import { DEFAULT_TARGET, useFlipbook, useSeqResult, useSequence, useTarget } from '../hooks'
import { readUrl, writeUrl } from '../url'
import Catalogs from './Catalogs'
import FoundPanel from './FoundPanel'
import LayersPanel, { Group } from './LayersPanel'
import Player, { FrameRows, StackRows, type Flipbook } from './Player'
import PlotsPanel from './PlotsPanel'
import ResearchPanel from './ResearchPanel'
import SelectionTable from './SelectionTable'
import SkyView from './SkyView'
import TargetBar from './TargetBar'
import TimeWindow from './TimeWindow'
import UcdSearch from './UcdSearch'

/** Explore (plain findings, expert tools behind "Show advanced") and Research (everything + numbers) share this layout. */
export default function Workbench({ mode }: { mode: 'explore' | 'research' }) {
  const [initialUrl] = useState(readUrl)
  const { resolved, lookup, goTo, busy, error } = useTarget()
  const [opts, setOpts] = useState<SeqOptions>({})
  const { seq, error: seqError } = useSequence(resolved, opts)
  const summary = useSeqResult(seq, getSummary)
  const [advanced, setAdvanced] = useState(mode === 'research')
  // name put into the target box from outside (UCD table click); remounts TargetBar with it
  const [picked, setPicked] = useState<string | null>(null)
  const [aladin, setAladin] = useState<Aladin | null>(null)
  const [fb, setFb] = useFlipbook()
  const [known, setKnown] = useState<Ucd | null>(null)
  const [skyUcds, setSkyUcds] = useState<Ucd[]>([])
  const [spiffOn, setSpiffOn] = useState(false)
  const [catalogCount, setCatalogCount] = useState(0)
  const [fov, setFov] = useState(initialUrl.fov ?? 0.25)
  const [selection, setSelection] = useState<Source[][] | null>(null)
  const [compareA, setCompareA] = useState<string | null>(null)
  const [stackBand, setStackBand] = useState<string | null>(null)
  const asteroidCat = useRef<Catalog | null>(null)

  const setFlipbook = useCallback(
    (patch: Partial<Flipbook>) => {
      if (patch.frameId) setStackBand(null) // picking a frame leaves the stack view
      setFb(patch)
    },
    [setFb],
  )

  const frameById = (id: string | null) => seq?.frames.find((f) => f.id === id)
  const frameA = frameById(compareA)
  const frameB = compareA && fb.frameId !== compareA ? frameById(fb.frameId) : undefined
  const override =
    seq && frameA && frameB
      ? {
          png: `/api/sequences/${seq.id}/diff.png?a=${encodeURIComponent(frameA.id)}&b=${encodeURIComponent(frameB.id)}`,
          label: `Difference ${frameB.date.slice(0, 10)} ${frameB.band} − ${frameA.date.slice(0, 10)} ${frameA.band} (red = new, blue = old)`,
        }
      : seq && stackBand
        ? { png: `/api/sequences/${seq.id}/stack.png?band=${stackBand}&n=${seq.frames.length}`, label: `Median stack ${stackBand}` }
        : null
  const canSelect = catalogCount > 0 && fov < 0.5

  useEffect(() => {
    setCompareA(null)
    setStackBand(null)
    setSelection(null)
    setKnown(null)
    if (resolved) ucdsNear(resolved).then((r) => setKnown(r[0] ?? null)).catch(() => setKnown(null))
  }, [resolved])

  // known asteroids from the summary as a sky catalog
  const asteroids = summary.data?.asteroids
  useEffect(() => {
    if (!aladin) return
    if (!asteroidCat.current) {
      asteroidCat.current = A.catalog({ name: 'Known asteroids', color: '#facc15', sourceSize: 14, onClick: 'showTable' })
      aladin.addCatalog(asteroidCat.current)
    }
    asteroidCat.current.removeAll()
    asteroidCat.current.addSources((asteroids ?? []).map((a) => A.source(a.ra, a.dec, { name: a.name, mjd: a.mjd, rate_arcsec_h: a.rate_arcsec_h })))
  }, [aladin, asteroids])

  const pickUcd = (u: Ucd) => {
    setFlipbook({ frameId: null, playing: false, excluded: new Set() })
    setPicked(u.designation)
    goTo({ name: u.designation, ra: u.ra, dec: u.dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: u.spiff_autotype })
  }

  return (
    <div className="flex h-full flex-col">
      <TargetBar
        key={picked}
        initial={picked ?? initialUrl.target ?? DEFAULT_TARGET}
        resolved={resolved}
        busy={busy}
        error={error ?? seqError}
        onSubmit={(q) => {
          setFlipbook({ frameId: null, playing: false, excluded: new Set() })
          writeUrl({ frame: null })
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
                onFov={setFov}
              />
            )}
            {advanced && (
              <button
                className="absolute top-2 left-1/2 z-10 -translate-x-1/2 rounded bg-slate-800/90 px-2 py-1 text-xs enabled:hover:bg-slate-700 disabled:text-slate-500"
                disabled={!canSelect}
                title="Drag a rectangle to list catalog sources inside it. Needs at least one visible catalog layer and a field of view under 0.5°."
                onClick={() => aladin?.select('rect', (_shape, groups) => setSelection(groups))}
              >
                ⬚ Select region
              </button>
            )}
            {selection && <SelectionTable groups={selection} onClose={() => setSelection(null)} />}
          </div>
          <div className="flex h-72 shrink-0 border-t border-slate-700 bg-slate-900">
            <div className="min-w-0 flex-1">
              <PlotsPanel seq={seq} periods={candidatePeriods(summary.data?.variability)} />
            </div>
            {/* hidden, not unmounted, so layer/catalog toggles keep their state */}
            <div className={`w-[30rem] shrink-0 border-l border-slate-700 ${advanced ? '' : 'hidden'}`}>
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
        <aside className="w-96 shrink-0 overflow-y-auto border-l border-slate-700 bg-slate-900">
          <Player seq={seq} fb={fb} set={setFlipbook} aladin={aladin} override={override}>
            {(cur) =>
              advanced && (
                <div className="flex items-center gap-2">
                  <button
                    className={`rounded px-2 py-1 ${compareA ? 'bg-amber-700' : 'bg-slate-700'}`}
                    disabled={(!compareA && !cur) || fb.deep}
                    title={fb.deep ? 'Compare works on single frames; turn off Deep stacks' : undefined}
                    onClick={() => {
                      setStackBand(null)
                      setCompareA(compareA ? null : (cur?.id ?? null))
                    }}
                  >
                    {compareA ? 'Clear compare' : 'Compare'}
                  </button>
                  <span className="text-slate-500">
                    {compareA ? (frameB ? '' : `A = ${frameA?.date.slice(0, 10)} ${frameA?.band}; pick frame B`) : 'Pin the current frame as A'}
                  </span>
                </div>
              )
            }
          </Player>
          {mode === 'explore' ? (
            <Group title="What we found">
              <FoundPanel summary={summary.data} note={summary.note} busy={summary.busy} />
            </Group>
          ) : (
            <>
              <Group title="Measurements">
                <ResearchPanel seq={seq} summary={summary.data} note={summary.note} busy={summary.busy} />
              </Group>
              <Group title="Fetch exposures for a time window">
                <TimeWindow
                  value={opts}
                  onApply={(o) => {
                    setFlipbook({ frameId: null, playing: false, excluded: new Set() })
                    setOpts(o)
                  }}
                />
              </Group>
            </>
          )}
          <div className={advanced ? '' : 'hidden'}>
            <LayersPanel
              aladin={aladin}
              frames={
                <>
                  <FrameRows seq={seq} fb={fb} set={setFlipbook} />
                  <StackRows
                    seq={seq}
                    band={stackBand}
                    onPick={(b) => {
                      setCompareA(null)
                      setFlipbook({ playing: false })
                      setStackBand(b)
                    }}
                  />
                </>
              }
              catalogs={
                aladin && (
                  <Catalogs aladin={aladin} ucds={skyUcds} spiffOn={spiffOn} setSpiffOn={setSpiffOn} onVisibleCount={setCatalogCount} />
                )
              }
            />
          </div>
        </aside>
      </div>
    </div>
  )
}
