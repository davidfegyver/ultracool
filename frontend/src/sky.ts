/** Small sky-geometry helpers shared by the flipbook overlays (no WCS library needed: the grid is a plain TAN/CDELT WCS). */

const RAD = Math.PI / 180

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

/** A labelled circle drawn on the flipbook (grid px, PNG convention). `faint` = dashed (expected but not there now);
 * `small` = minor point, e.g. one step of a predicted track. */
export type Mark = { x: number; y: number; label?: string; faint?: boolean; small?: boolean }
