/** Small sky-geometry helpers shared by the flipbook overlays (no WCS library needed: the grid is a plain TAN/CDELT WCS). */

const RAD = Math.PI / 180
/** grid pixel scale (WISE native) of every sequence */
export const PIX_ARCSEC = 2.75
/** backend photometry aperture radii (SPHEREx 2 native px, WISE 3 grid px) and sky annuli, in arcsec */
export const APERTURE: Record<'spherex' | 'wise', { r: number; sky: [number, number] }> = {
  spherex: { r: 12.3, sky: [24.6, 43] },
  wise: { r: 8.25, sky: [50, 70] },
}
/** grid-centre epoch 2018.0 of every sequence */
export const MJD_2018 = 58119
export const MJD_2000 = 51544.5

export const mjdToYear = (mjd: number) => 2000 + (mjd - 51544.5) / 365.25
export const mjdToIso = (mjd: number) => new Date((mjd - 40587) * 864e5).toISOString()

/** Linear proper-motion propagation, same formula as the backend's frames.propagate. */
export function propagate(ra: number, dec: number, pmra_masyr: number, pmdec_masyr: number, epoch_yr: number, mjd: number) {
  const dt = mjdToYear(mjd) - epoch_yr
  return { ra: ra + (pmra_masyr / 3.6e6 / Math.cos(dec * RAD)) * dt, dec: dec + (pmdec_masyr / 3.6e6) * dt }
}

/** ICRS degrees → grid pixel [x, y_png] (0-based, PNG rows top-down, like frame.target_px). */
export function worldToPx(wcs: Record<string, string | number>, height: number, ra: number, dec: number): [number, number] {
  const [a0, d0] = [Number(wcs.CRVAL1) * RAD, Number(wcs.CRVAL2) * RAD]
  const [a, d] = [ra * RAD, dec * RAD]
  const cosc = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a - a0)
  const xi = (Math.cos(d) * Math.sin(a - a0)) / cosc / RAD
  const eta = (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a - a0)) / cosc / RAD
  const x = Number(wcs.CRPIX1) - 1 + xi / Number(wcs.CDELT1)
  const y = Number(wcs.CRPIX2) - 1 + eta / Number(wcs.CDELT2)
  return [x, height - 1 - y]
}

/** Inverse of worldToPx: grid pixel [x, y_png] → ICRS degrees. */
export function pxToWorld(wcs: Record<string, string | number>, height: number, x: number, yPng: number) {
  const xi = (x - Number(wcs.CRPIX1) + 1) * Number(wcs.CDELT1) * RAD
  const eta = (height - 1 - yPng - Number(wcs.CRPIX2) + 1) * Number(wcs.CDELT2) * RAD
  const [a0, d0] = [Number(wcs.CRVAL1) * RAD, Number(wcs.CRVAL2) * RAD]
  const den = Math.cos(d0) - eta * Math.sin(d0)
  const ra = (a0 + Math.atan2(xi, den)) / RAD
  return { ra: ((ra % 360) + 360) % 360, dec: Math.atan2(Math.sin(d0) + eta * Math.cos(d0), Math.hypot(xi, den)) / RAD }
}

/** A labelled circle drawn on the flipbook (grid px, PNG convention). `faint` = dashed (expected but not there now);
 * `small` = minor point, e.g. one step of a predicted track. */
export type Mark = { x: number; y: number; label?: string; faint?: boolean; small?: boolean }
