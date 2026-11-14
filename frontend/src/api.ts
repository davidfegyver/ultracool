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

async function get<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new Error(body?.detail ?? `${r.status} ${r.statusText}`)
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
  mjd: number
  date: string
  wavelength_um: number | null
  epoch_index: number
  flux_ujy: number | null
  flux_err_ujy: number | null
  flagged: boolean
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
}

export const startSequence = (r: Resolved) =>
  get<{ id: string }>('/api/sequences', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ra: r.ra, dec: r.dec, pmra_masyr: r.pmra_masyr, pmdec_masyr: r.pmdec_masyr, epoch_yr: r.epoch_yr }),
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
