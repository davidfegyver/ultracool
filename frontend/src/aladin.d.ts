// aladin-lite ships no type declarations; only the surface this app uses.
declare module 'aladin-lite' {
  export interface ImageLayer {
    setOpacity(o: number): void
    setSliceNumber(n: number): void
  }
  export interface Source {
    ra: number
    dec: number
    data: Record<string, unknown>
  }
  export interface Catalog {
    name: string
    show(): void
    hide(): void
    addSources(s: Source[]): void
    removeAll(): void
  }
  export interface Aladin {
    gotoRaDec(ra: number, dec: number): void
    getFov(): [number, number]
    setBaseImageLayer(idOrLayer: string | ImageLayer): void
    getRaDec(): [number, number]
    newImageSurvey(id: string, opts?: Record<string, unknown>): ImageLayer
    setOverlayImageLayer(layer: ImageLayer, name: string): ImageLayer
    removeImageLayer(name: string): void
    addCatalog(c: Catalog): void
    /** canvas px → [ra, dec]; throws or returns non-finite values off the projection */
    pix2world(x: number, y: number): [number, number]
    on(event: string, cb: (...args: unknown[]) => void): void
  }
  const A: {
    init: Promise<void>
    aladin(div: HTMLElement, opts: Record<string, unknown>): Aladin
    image(url: string, opts: Record<string, unknown>): ImageLayer
    catalog(opts: Record<string, unknown>): Catalog
    source(ra: number, dec: number, data: Record<string, unknown>): Source
    catalogFromURL(url: string, opts: Record<string, unknown>): Catalog
  }
  export default A
}
