export type Resolved = {
  name: string | null
  ra: number
  dec: number
  pmra_masyr: number
  pmdec_masyr: number
  epoch_yr: number
  otype: string | null
  sptype: string | null
}

/** HTTP error with its status, so a 404 from a not-yet-deployed endpoint can read "not available yet". */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}
export const isMissing = (e: unknown) => e instanceof ApiError && e.status === 404

async function get<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : `${r.status} ${r.statusText}`, r.status)
  }
  return r.json()
}

const qs = (params: Record<string, string | number | null | undefined>) =>
  new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== null && v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)]),
  ).toString()

export const resolveTarget = (q: string) => get<Resolved>(`/api/resolve?${qs({ q })}`)

export type Frame = {
  id: string
  survey: 'spherex' | 'wise'
  band: string
  /** single SPHEREx frame, WISE visit median, or one WISE exposure */
  kind?: 'single' | 'visit' | 'exposure'
  mjd: number
  date: string
  wavelength_um: number | null
  epoch_index: number
  flux_ujy: number | null
  flux_err_ujy: number | null
  flagged: boolean
  /** artifact flags hit at the target, e.g. GHOST, PERSIST, STREAK */
  flag_names?: string[]
  target_px: [number, number]
  png: string
}

export type Sequence = {
  id: string
  status: 'querying' | 'fetching' | 'done' | 'error'
  total: number
  done: number
  error: string | null
  grid: { wcs: Record<string, string | number>; width: number; height: number }
  target: { ra: number; dec: number; pmra_masyr: number; pmdec_masyr: number; epoch_yr: number }
  frames: Frame[]
  /** all WISE frames processed (SPHEREx may still be fetching); absent on older backends */
  wise_done?: boolean
}

/** Optional sequence parameters; wise_exposures needs mjd_max - mjd_min <= 30 (else HTTP 400). */
export type SeqOptions = {
  fov_deg?: number
  mjd_min?: number
  mjd_max?: number
  wise_exposures?: boolean
}

/** `priority_bands`: frames of these bands are processed first; not part of the sequence id. */
export const startSequence = (r: Resolved, opts: SeqOptions & { priority_bands?: string[] } = {}) =>
  get<{ id: string }>('/api/sequences', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ra: r.ra, dec: r.dec, pmra_masyr: r.pmra_masyr, pmdec_masyr: r.pmdec_masyr, epoch_yr: r.epoch_yr, ...opts }),
  })

export const getSequence = (id: string) => get<Sequence>(`/api/sequences/${id}`)

export type SpecFit = { label: string; prob: number; chi2_red: number; n_bins: number }
export type Spectrum = {
  verdict: string
  best: SpecFit | null
  ranking: SpecFit[]
  binned: { wavelength_um: number; flambda: number; err: number }[]
  template_curve: { label: string; wavelength_um: number[]; flambda: number[] } | null
}
export const getSpectrum = (id: string) => get<Spectrum>(`/api/sequences/${id}/spectrum`)

/** WISE catalog photometry (NEOWISE single-exposure catalog, per visit): the fallback light curve for saturated stars. */
export type CatalogLightcurve = {
  source: string
  status: string
  points: { mjd: number; band: string; flux_ujy: number | null; flux_err_ujy: number | null; mag: number | null; mag_err: number | null; n: number }[]
}
export const getCatalogLightcurve = (id: string) => get<CatalogLightcurve>(`/api/sequences/${id}/catalog_lightcurve`)

export type MotionPoint = { mjd: number; band: string; ra: number; dec: number; err_arcsec: number }
export type Summary = {
  motion: {
    status: 'ok' | 'insufficient data'
    pmra_masyr: number | null
    pmdec_masyr: number | null
    pmra_err_masyr: number | null
    pmdec_err_masyr: number | null
    pm_total_arcsec_yr: number | null
    significance_sigma: number | null
    baseline_yr: number | null
    n_epochs: number | null
    catalog: { pmra_masyr: number; pmdec_masyr: number } | null
    consistent_with_catalog: boolean | null
    verdict: 'moving' | 'not moving' | 'insufficient data'
    points: MotionPoint[]
  }
  color: {
    w1_w2: number | null
    w1_w2_err: number | null
    /** W1 undetected: w1_w2 is a lower limit */
    w1_w2_is_lower_limit?: boolean
    verdict: 'extremely red (Y/late-T dwarf-like)' | 'red (L/T dwarf-like)' | 'normal star colors' | 'insufficient data'
  }
  variability: {
    bands: Record<string, { n: number; chi2_red: number | null; amplitude_mag: number | null }>
    verdict: 'periodic variable' | 'irregular variable' | 'constant' | 'insufficient data'
    period_days: number | null
    /** best period may be an alias of the WISE 6-month / 1-year cadence */
    period_alias_warning?: boolean
    /** Lomb-Scargle false-alarm probability of the best peak */
    fap?: number | null
    /** periods the 6-month WISE cadence cannot tell apart from period_days */
    period_alternatives_days?: number[]
    /** light curve used: own pipeline photometry or WISE catalog photometry (saturated stars) */
    source?: 'pipeline' | 'catalog'
    source_note?: string
  }
  spectrum: Spectrum | null
  asteroids?: KnownAsteroid[]
  plain: string[]
}
export type KnownAsteroid = { name: string; ra: number; dec: number; mjd: number; rate_arcsec_h: number }
export const getSummary = (id: string) => get<Summary>(`/api/sequences/${id}/summary`)
/** best period first, then the cadence aliases: the "Fold at" choices */
export const candidatePeriods = (v: Summary['variability'] | undefined) => (v?.period_days ? [v.period_days, ...(v.period_alternatives_days ?? [])] : [])

export type Mover = {
  ra: number
  dec: number
  /** grid pixels, PNG convention (y down) */
  x_px: number
  y_px: number
  pmra_masyr: number
  pmdec_masyr: number
  pm_err_masyr: number
  significance_sigma: number
  w1_w2: number | null
  known: { simbad: string | null; catwise: string | null; spiff: string | null }
  is_target: boolean
  /** indices of movers sharing this proper motion (common-proper-motion companions) */
  cpm_with?: (number | 'target')[]
  /** epoch of ra/dec/x_px/y_px (2018.0, the grid-centre epoch) */
  epoch_yr?: number
}
export const getMovers = (id: string) => get<{ movers: Mover[]; status: 'ok' | 'insufficient data' }>(`/api/sequences/${id}/movers`)

export const exportCsvUrl = (id: string) => `/api/sequences/${id}/export.csv`

export type Ucd = {
  designation: string
  ra: number
  dec: number
  dataset: string
  spiff_autotype: string
  spiff_chi2_r: number | null
  literature_spectral_type: string | null
}
export const searchUcds = (p: { spt_min?: string; spt_max?: string; dataset?: string; limit?: number }) =>
  get<Ucd[]>(`/api/ucds?${qs(p)}`)
export const ucdDatasets = () => get<string[]>('/api/ucds/datasets')
export const ucdsNear = (r: Resolved) =>
  get<(Ucd & { sep_arcsec: number })[]>(
    `/api/ucds/near?${qs({ ra: r.ra, dec: r.dec, pmra_masyr: r.pmra_masyr, pmdec_masyr: r.pmdec_masyr, epoch_yr: r.epoch_yr })}`,
  )
