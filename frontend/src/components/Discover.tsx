import { useState } from 'react'
import { getMovers, getSummary, type Mover, type Sequence } from '../api'
import { downloadCsv } from '../csv'
import { DEFAULT_TARGET, useFlipbook, useProbe, useSeqResult, useSequence, useTarget, type ProbeCtl, type ProbePoint } from '../hooks'
import { propagate } from '../sky'
import { readUrl } from '../url'
import Player from './Player'
import Pending from './Pending'
import { ProbeMenu, ProbePanel } from './Probe'
import { AsteroidList } from './ResearchPanel'
import TargetBar from './TargetBar'
import Term from './Term'

const FIELD_FOV = 0.25 // widest grid the backend allows: most candidates per run
const PIX_ARCSEC = 2.75
const LABELS_KEY = 'ultracool-discover-labels'
const LABELS = ['Real mover', 'Artifact', 'Unsure'] as const
type Label = (typeof LABELS)[number]
type Classification = Mover & { label: Label; sequence_id: string; field: string; classified_at: string }

const key = (m: Mover) => `${m.ra.toFixed(5)} ${m.dec.toFixed(5)}`
const loadLabels = (): Record<string, Classification> => {
  try {
    return JSON.parse(localStorage.getItem(LABELS_KEY) ?? '{}')
  } catch {
    return {}
  }
}

/** Random point with |b| > 30° (uniform on the sphere), in ICRS degrees: away from the crowded Milky Way plane. */
function randomHighLatitude() {
  const rad = Math.PI / 180
  const l = Math.random() * 360
  const b = Math.asin(0.5 + Math.random() * 0.5) * (Math.random() < 0.5 ? -1 : 1) / rad
  // galactic -> ICRS: north galactic pole (192.85948, 27.12825), l of the north celestial pole 122.93192
  const [aP, dP, lN] = [192.85948 * rad, 27.12825 * rad, 122.93192 * rad]
  const [lr, br] = [l * rad, b * rad]
  const dec = Math.asin(Math.sin(br) * Math.sin(dP) + Math.cos(br) * Math.cos(dP) * Math.cos(lN - lr))
  const ra = aP + Math.atan2(Math.cos(br) * Math.sin(lN - lr), Math.sin(br) * Math.cos(dP) - Math.cos(br) * Math.sin(dP) * Math.cos(lN - lr))
  return { l, b, ra: ((ra / rad) % 360 + 360) % 360, dec: dec / rad }
}

/** Discover mode: run a field, list automatically detected movers, review each one in a cropped deep-stack flipbook. */
export default function Discover() {
  const [initialUrl] = useState(readUrl)
  const { resolved, lookup, goTo, busy, error } = useTarget()
  const [field, setField] = useState(0) // remounts TargetBar when a random field replaces the text
  const { seq, error: seqError } = useSequence(resolved, { fov_deg: FIELD_FOV }, ['W2'])
  // movers come from WISE: ask as soon as all WISE frames are in instead of waiting for SPHEREx
  const movers = useSeqResult(seq, getMovers, true)
  const summary = useSeqResult(seq, getSummary)
  const probe = useProbe(seq?.id)
  const [sel, setSel] = useState(0)
  const [labels, setLabels] = useState(loadLabels)
  const list = movers.data?.movers ?? []
  const cur = list[sel] as Mover | undefined

  const classify = (m: Mover, label: Label) => {
    const next = {
      ...labels,
      [key(m)]: { ...m, label, sequence_id: seq!.id, field: resolved?.name ?? `${resolved?.ra} ${resolved?.dec}`, classified_at: new Date().toISOString() },
    }
    localStorage.setItem(LABELS_KEY, JSON.stringify(next))
    setLabels(next)
    if (sel < list.length - 1) setSel(sel + 1)
  }
  const exportLabels = () => {
    const rows = Object.values(labels).map((c) => ({ ...c, simbad: c.known.simbad, catwise: c.known.catwise, spiff: c.known.spiff }))
    const cols = ['label', 'ra', 'dec', 'pmra_masyr', 'pmdec_masyr', 'pm_err_masyr', 'significance_sigma', 'w1_w2', 'simbad', 'catwise', 'spiff', 'is_target', 'field', 'sequence_id', 'classified_at']
    downloadCsv('ultracool_classifications.csv', cols, rows)
  }

  return (
    <div className="flex h-full flex-col">
      <TargetBar
        key={field}
        initial={resolved ? (resolved.name ?? `${resolved.ra.toFixed(5)} ${resolved.dec.toFixed(5)}`) : (initialUrl.target ?? DEFAULT_TARGET)}
        resolved={resolved}
        busy={busy}
        error={error ?? seqError}
        onSubmit={(q) => {
          setSel(0)
          probe.place(null)
          lookup(q)
        }}
        quick={[]}
      >
        <button
          className="rounded bg-emerald-800 px-2 py-1 text-xs hover:bg-emerald-700"
          title="A random spot more than 30° from the Milky Way plane, where background stars are sparse"
          onClick={() => {
            const f = randomHighLatitude()
            setSel(0)
            probe.place(null)
            setField(field + 1)
            goTo({ name: `Random field l=${f.l.toFixed(1)}° b=${f.b.toFixed(1)}°`, ra: f.ra, dec: f.dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: null })
          }}
        >
          Random high-latitude field
        </button>
      </TargetBar>
      <div className="flex min-h-0 flex-1">
        <section aria-label="Candidates" className="w-96 shrink-0 overflow-y-auto border-r border-slate-700 bg-slate-900 text-xs">
          <h2 className="bg-slate-800 px-2 py-1 font-semibold tracking-wide text-slate-300 uppercase">
            Moving candidates {list.length > 0 && `(${list.length})`}
          </h2>
          {!movers.data && (movers.note ? <Pending note={movers.note} busy={movers.busy} className="p-2" /> : <p className="p-2 text-slate-500">Pick a field to scan</p>)}
          {seq?.wise_done && (seq.status === 'querying' || seq.status === 'fetching') && (
            <Pending note={`SPHEREx frames still loading (${seq.done}/${seq.total})`} busy className="px-2 pt-1" />
          )}
          {movers.data?.status === 'insufficient data' && <p className="p-2 text-slate-500">Not enough epochs in this field to measure motion.</p>}
          {movers.data?.status === 'ok' && !list.length && <p className="p-2 text-slate-500">No significant movers in this field.</p>}
          <ol>
            {list.map((m, i) => (
              <li key={key(m)}>
                <button
                  aria-current={i === sel}
                  className={`w-full border-b border-slate-800 px-2 py-1.5 text-left ${i === sel ? 'bg-sky-900' : 'hover:bg-slate-800'}`}
                  onClick={() => setSel(i)}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">#{i}</span>
                    <span>{(Math.hypot(m.pmra_masyr, m.pmdec_masyr) / 1000).toFixed(2)}″/yr</span>
                    <span className="text-slate-400">{m.significance_sigma.toFixed(1)}σ</span>
                    {m.w1_w2 !== null && <span className="text-slate-400">W1−W2 {m.w1_w2.toFixed(2)}</span>}
                    {labels[key(m)] && <span className="ml-auto rounded bg-slate-700 px-1">{labels[key(m)].label}</span>}
                  </div>
                  <KnownBadges m={m} />
                </button>
              </li>
            ))}
          </ol>
          {summary.data?.asteroids && (
            <div className="p-2">
              <AsteroidList asteroids={summary.data.asteroids} />
            </div>
          )}
        </section>
        <section aria-label="Candidate review" className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          {cur && seq ? (
            <Review key={key(cur)} seq={seq} m={cur} i={sel} label={labels[key(cur)]?.label} onLabel={(l) => classify(cur, l)} probe={probe} />
          ) : (
            <div className="space-y-2 p-4 text-sm text-slate-400">
              <p>
                Discover scans a {FIELD_FOV}° patch of sky for everything that moves over 16 years. Nearby stars and{' '}
                <Term k="brown dwarf">brown dwarfs</Term> drift a little every year (<Term k="proper motion" />). Candidates nobody has catalogued yet are marked{' '}
                <span className="rounded bg-amber-700 px-1 text-xs text-white">Unknown</span>.
              </p>
              <p>For each candidate: play the flipbook, decide whether the dot really moves along the dashed track, and click Real mover, Artifact or Unsure.</p>
            </div>
          )}
          {seq && (
            <section aria-label="Probe" className="mx-3 mb-3 max-w-3xl rounded border border-slate-700">
              <h3 className="bg-slate-800 px-2 py-1 text-xs font-semibold tracking-wide text-slate-300 uppercase">Probe</h3>
              <ProbePanel probe={probe} research={false} />
            </section>
          )}
          <ProbeMenu
            probe={probe}
            onCentre={(p: ProbePoint) => {
              setSel(0)
              setField(field + 1)
              goTo({ name: null, ...p, epoch_yr: 2000, otype: null, sptype: null })
            }}
          />
          <div className="mt-auto flex items-center gap-2 border-t border-slate-700 p-2 text-xs">
            <span className="text-slate-400">{Object.keys(labels).length} classifications saved in this browser</span>
            <button className="rounded bg-slate-700 px-2 py-1 enabled:hover:bg-slate-600 disabled:opacity-50" disabled={!Object.keys(labels).length} onClick={exportLabels}>
              ⤓ Export CSV
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

function KnownBadges({ m }: { m: Mover }) {
  const names = [['SIMBAD', m.known.simbad], ['CatWISE', m.known.catwise], ['SPIFF', m.known.spiff]].filter(([, v]) => v) as [string, string][]
  return (
    <div className="mt-0.5 flex flex-wrap gap-1">
      {m.is_target && <span className="rounded bg-pink-800 px-1">target</span>}
      {names.length ? (
        names.map(([cat, v]) => (
          <span key={cat} className="rounded bg-slate-700 px-1 text-slate-300">
            {cat}: {v}
          </span>
        ))
      ) : (
        <span className="rounded bg-amber-700 px-1 text-white">Unknown: not in SIMBAD, CatWISE or SPIFF</span>
      )}
      {m.cpm_with?.length ? (
        <span className="rounded bg-violet-800 px-1">moves together with {m.cpm_with.map((c) => (c === 'target' ? 'the target' : `#${c}`)).join(', ')}</span>
      ) : null}
    </div>
  )
}

function Review({ seq, m, i, label, onLabel, probe }: { seq: Sequence; m: Mover; i: number; label?: Label; onLabel: (l: Label) => void; probe: ProbeCtl }) {
  const [fb, setFb] = useFlipbook({ bands: ['W1', 'W2'], deep: true, frameId: null, showOnSky: false })
  const vx = -m.pmra_masyr / 1000 / PIX_ARCSEC // east = -x on the grid
  const vy = -m.pmdec_masyr / 1000 / PIX_ARCSEC // north = up = -y in PNG rows
  const size = Math.min(Math.max(seq.grid.width, seq.grid.height), Math.max(40, 16 * Math.hypot(vx, vy) + 30))
  return (
    <div className="flex flex-wrap gap-4 p-3">
      <div className="w-[376px]">
        <Player seq={seq} fb={fb} set={setFb} aladin={null} focus={{ x: m.x_px, y: m.y_px, size, vx, vy }} probe={probe} />
      </div>
      <div className="min-w-64 flex-1 space-y-2 text-sm">
        <h2 className="text-lg font-semibold">Candidate #{i}</h2>
        <KnownBadges m={m} />
        <table className="text-xs">
          <tbody>
            {[
              ['RA, Dec (2018.0)', `${m.ra.toFixed(5)}, ${m.dec.toFixed(5)}`],
              ['μα*, μδ (mas/yr)', `${m.pmra_masyr.toFixed(0)}, ${m.pmdec_masyr.toFixed(0)} ± ${m.pm_err_masyr.toFixed(0)}`],
              ['Significance', `${m.significance_sigma.toFixed(1)}σ`],
              ['W1−W2', m.w1_w2 === null ? '—' : m.w1_w2.toFixed(2)],
            ].map(([k, v]) => (
              <tr key={k}>
                <th className="pr-3 text-left font-normal text-slate-400">{k}</th>
                <td className="font-mono">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-slate-400">
          The dashed line is the fitted 16-year track; the pink circle is where the fit puts the source on each date. A real mover stays inside the circle in every
          stack; an <Term k="artifact" /> appears in only one stack or band.
        </p>
        <div role="group" aria-label="Classify candidate" className="flex gap-2">
          {LABELS.map((l) => (
            <button
              key={l}
              aria-pressed={label === l}
              className={`rounded px-3 py-1 ${label === l ? 'bg-sky-600' : 'bg-slate-700 hover:bg-slate-600'}`}
              onClick={() => onLabel(l)}
            >
              {l}
            </button>
          ))}
        </div>
        <button
          className="rounded bg-cyan-800 px-3 py-1 text-xs hover:bg-cyan-700"
          title="Put the probe on this candidate with its proper motion and take a quick photometry preview"
          onClick={() => {
            // mover positions are at epoch_yr (2018.0); the probe works at epoch 2000
            const at = propagate(m.ra, m.dec, m.pmra_masyr, m.pmdec_masyr, m.epoch_yr ?? 2018, 51544.5)
            const p = { ...at, pmra_masyr: m.pmra_masyr, pmdec_masyr: m.pmdec_masyr }
            probe.place(p)
            probe.measure('preview', p)
          }}
        >
          Measure
        </button>
      </div>
    </div>
  )
}
