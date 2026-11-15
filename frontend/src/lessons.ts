/** Learn-mode lesson path. Each lesson pre-configures the flipbook; swap objects/windows here without touching components.
 * Objects, windows, markers and quizzes are the specs we verified against the data (see docs/validation.md). */

/** A labelled circle on the flipbook. With pm: follows the object. With `mjd`: an image feature tied to that season
 * (shown solid within ±60 days of the same time of year, dashed otherwise). */
export type Marker = {
  label: string
  ra: number
  dec: number
  pmra_masyr?: number
  pmdec_masyr?: number
  epoch_yr?: number
  mjd?: number
}

export type Lesson = {
  id: string
  title: string
  skill: string
  object: string
  /** name for /api/resolve; or give ra/dec (+ pm, epoch) directly */
  target?: string
  ra?: number
  dec?: number
  pmra_masyr?: number
  pmdec_masyr?: number
  epoch_yr?: number
  fov_deg?: number
  mjd_min?: number
  mjd_max?: number
  /** every WISE exposure as its own frame (needs mjd window <= 30 d) */
  wise_exposures?: boolean
  bands: string[]
  /** start in deep-stack mode */
  deep?: boolean
  /** MJD windows: W1 and W2 deep stacks of each window are shown side by side */
  stack_windows?: [number, number][]
  /** objects/features to circle instead of the target circle */
  markers?: Marker[]
  /** predicted positions of a solar-system object; the point nearest each exposure is circled */
  track?: { mjd: number; ra: number; dec: number }[]
  /** known period, offered first under "Fold at": WISE's 6-month cadence can make the periodogram pick an alias */
  period_days?: number
  /** light curve is the main view (shown above the flipbook) */
  light_curve_first?: boolean
  /** hide the light curve and show this sentence instead */
  hide_light_curve?: string
  /** "Try it on another object" after the quiz: query params of the page it opens (mode plus target or position).
   * Names were checked against /api/resolve. */
  try_next?: { object: string; params: Record<string, string>; note: string }
  /** more real-world examples of the lesson's point; each item opens in Explore mode at its position */
  more_examples?: { title: string; intro: string; items: { name: string; ra: number; dec: number; reason: string }[] }
  story: string
  look_for: string
  quiz: { question: string; options: string[]; answer_index: number; explanation: string }
}

const EPS_IND_A = { ra: 330.8402234423433, dec: -56.785978554364995, pmra_masyr: 3966.661, pmdec_masyr: -2536.192, epoch_yr: 2000 }
const EPS_IND_B = { ra: 331.04414658852124, dec: -56.782844195116105, pmra_masyr: 3981.977, pmdec_masyr: -2466.832, epoch_yr: 2000 }

export const LESSONS: Lesson[] = [
  {
    id: 'moves',
    title: 'A moving star',
    skill: 'Spot a moving star',
    object: "Barnard's Star",
    ra: 269.4520769586187,
    dec: 4.693364966576667,
    pmra_masyr: -801.551,
    pmdec_masyr: 10362.394,
    epoch_yr: 2000,
    fov_deg: 0.076,
    bands: ['W2', 'D6'],
    try_next: { object: 'Proxima Centauri', params: { mode: 'explore', target: 'Proxima Cen' }, note: 'the nearest star to the Sun, crossing almost 4 arcseconds of sky every year' },
    hide_light_curve: 'Too bright for brightness measurements; this lesson is about motion.',
    story:
      "Barnard's Star is a small red star only 6 light-years away, the fastest-moving star in our sky. Most stars are so far away that they look frozen in place for a lifetime, but Barnard's Star slides about 10 arcseconds every year. Over the 16 years of WISE and SPHEREx pictures, that adds up to a shift you can see by eye.",
    look_for:
      'Play the W2 frames from 2010 to 2024: the bright star slides upward (north) across the background stars, about 10 arcseconds every year, staying inside the pink circle. The background stars stay put.',
    quiz: {
      question: "Between 2010 and 2024 Barnard's Star moved about how far across the sky?",
      options: ['Not at all: stars are fixed', 'About 2.4 arcminutes (roughly 145 arcseconds)', 'About 1 degree (twice the Moon)', 'It jumped back and forth randomly'],
      answer_index: 1,
      explanation:
        'It moves 10.4 arcseconds per year (the fastest-moving star in the sky), so 14 years add up to ~145 arcseconds, about 50 WISE pixels.',
    },
  },
  {
    id: 'color',
    title: 'A very cold brown dwarf',
    skill: 'Recognize a cold brown dwarf by its infrared color',
    object: 'WISE 0855−0714',
    ra: 133.81890825,
    dec: -7.247048,
    pmra_masyr: -8123.7,
    pmdec_masyr: 673.2,
    epoch_yr: 2000,
    fov_deg: 0.066,
    bands: ['W1', 'W2'],
    try_next: {
      object: 'WISE J2317−6659',
      params: { mode: 'explore', target: 'WISE J231728.42-665959.3' },
      note: 'a T dwarf about 30 parsecs away; this app gave it its first spectrum-based type (about T6)',
    },
    deep: true,
    stack_windows: [
      [56658, 57388],
      [58119, 58849],
      [59580, 60676],
    ],
    story:
      'WISE 0855−0714 is the coldest brown dwarf known: about 250–285 kelvin, roughly the temperature of a chilly day on Earth. It was found in 2014 only 7.4 light-years away. Something that cold gives off almost no visible light, and even in the infrared it is much brighter at 4.6 µm (WISE W2) than at 3.4 µm (W1), because methane and water in its atmosphere absorb the shorter wavelengths.',
    look_for:
      'Compare the W1 (3.4 µm) and W2 (4.6 µm) deep stacks at the circle: a faint dot is there in W2 but nothing at all in W1. Ordinary stars look about equally bright in both. Each stack adds up two years of pictures; switch periods to see it move too.',
    quiz: {
      question: 'The object shows up at 4.6 µm (W2) but is invisible at 3.4 µm (W1). What does that suggest?',
      options: ['It is a hot blue star', 'It is extremely cold, so almost all its light comes out at longer wavelengths', 'The W1 camera was broken', 'It is a galaxy'],
      answer_index: 1,
      explanation:
        'A ~250 K brown dwarf glows mainly beyond 4 µm, and methane absorbs its 3.4 µm light, so W1−W2 is huge (more than 3.5 mag here). Normal stars have W1−W2 near 0.',
    },
  },
  {
    id: 'together',
    title: 'Moving as a pair',
    skill: 'Find companions by common proper motion',
    object: 'Epsilon Indi A + Ba/Bb',
    // A-B midpoint (epoch 2000) moving with A's proper motion, so both stay in the 0.2° field
    ra: 330.94218,
    dec: -56.78441,
    pmra_masyr: 3966.661,
    pmdec_masyr: -2536.192,
    epoch_yr: 2000,
    fov_deg: 0.2,
    bands: ['W2'],
    try_next: { object: 'Gliese 229 B', params: { mode: 'explore', target: 'Gl 229 B' }, note: 'the first brown dwarf ever seen, moving together with its red-dwarf star' },
    hide_light_curve: 'This lesson is about how things move together, not about brightness.',
    markers: [
      { label: 'eps Ind A (K5V star)', ...EPS_IND_A },
      { label: 'eps Ind Ba/Bb (brown dwarfs)', ...EPS_IND_B },
    ],
    story:
      'Epsilon Indi A is a bright orange star 12 light-years away. In 2003 astronomers noticed a faint object 402″ away moving across the sky in exactly the same direction and at the same speed, about 4.7″ per year. It is a brown dwarf, soon after found to be a tight pair (Epsilon Indi Ba and Bb), orbiting the star from far away.',
    look_for:
      'Watch the bright star (A) and the faint dot ~400 arcseconds to its east (B), both circled: they drift the same way by the same amount (about 4.7 arcseconds per year) while the background stars stay still.',
    quiz: {
      question: 'Two objects 400 arcseconds apart move across the sky in exactly the same direction and speed for 14 years. Most likely they...',
      options: ['...are a coincidence', '...are bound together, travelling through space as one system', '...are both asteroids', '...are image artifacts'],
      answer_index: 1,
      explanation:
        'Moving together like this is the classic sign of a real pair. eps Ind B is a pair of brown dwarfs orbiting the star eps Ind A at ~1500 au.',
    },
  },
  {
    id: 'brightness',
    title: 'A pulsating star',
    skill: 'Read a periodic light curve',
    object: 'AL Bootis (Mira variable)',
    ra: 204.73282996689997,
    dec: 18.711619948339997,
    pmra_masyr: -1.924,
    pmdec_masyr: -1.836,
    epoch_yr: 2000,
    fov_deg: 0.05,
    bands: ['W1', 'W2'],
    period_days: 166.7,
    light_curve_first: true,
    try_next: {
      object: 'R Draconis',
      params: { mode: 'explore', target: 'R Dra' },
      note: 'a brighter Mira (period 246 d); too bright for our own photometry, so its light curve comes from the WISE catalog',
    },
    story:
      'AL Bootis is a Mira variable: an old red giant star that swells and shrinks, brightening and fading over a cycle of 166.7 days. WISE looked at it twice a year for over a decade, so the light curve catches it at many different points of its cycle.',
    look_for:
      'Open the light curve: AL Boo changes by about 1 magnitude (2.5× in brightness) at 3.4 and 4.6 µm. Because WISE only visits every 6 months, the plain plot looks like a slow wave; choose a period under "Fold at" above the plot and the points line up into one smooth repeating cycle.',
    quiz: {
      question:
        'A red giant star brightens and fades again and again, and folding the data at 167 days lines all points up into one smooth curve. What kind of variable is it?',
      options: ['An irregular young star', 'A pulsating Mira variable with a regular period', 'An asteroid', 'A brown dwarf'],
      answer_index: 1,
      explanation:
        "Mira variables are old red giants that swell and shrink with a stable period of 100–1000 days. AL Boo's 166.7 d period is recovered from WISE data alone.",
    },
  },
  {
    id: 'irregular',
    title: 'An irregular young star',
    skill: 'Tell irregular variability from periodic',
    object: 'RW Aurigae',
    ra: 76.95652603458333,
    dec: 30.401438173888888,
    pmra_masyr: 7.23,
    pmdec_masyr: -20.33,
    epoch_yr: 2000,
    fov_deg: 0.05,
    bands: ['W1', 'W2'],
    try_next: { object: 'T Tauri', params: { mode: 'explore', target: 'T Tau' }, note: 'the young star this whole class is named after, still wrapped in its dusty disk' },
    light_curve_first: true,
    story:
      'RW Aurigae is a very young star, a few million years old, still surrounded by a disk of gas and dust where planets may be forming. Since 2010 it has suddenly dimmed several times for months, when clumps of dust drifted in front of it, and the hot dust glows brightly in the infrared.',
    look_for:
      'Open the light curve: RW Aur brightens and fades by more than two magnitudes in W2 over the years, but with no repeating rhythm. Dust clumps in its disk block and unblock the light.',
    quiz: {
      question: "RW Aur's light curve rises and falls by large amounts but never repeats a regular cycle. Which explanation fits best?",
      options: ['A pulsating Mira star with a fixed period', 'Clumps of dust in a planet-forming disk passing in front of a young star', 'An eclipsing binary', 'A cosmic ray hit'],
      answer_index: 1,
      explanation:
        'RW Aur is a young T Tauri star with a messy disk; dimming events of years and month-long brightenings are irregular. We found no repeating cycle in the NEOWISE data.',
    },
  },
  {
    id: 'ghost',
    title: 'Camera ghosts',
    skill: 'Recognize image artifacts',
    object: 'Optical ghost of Epsilon Indi A',
    // 60″ east of A, moving with A: ghost (both seasons), A and B all fit in 0.25°
    ra: 330.8707,
    dec: -56.78598,
    pmra_masyr: 3966.661,
    pmdec_masyr: -2536.192,
    epoch_yr: 2000,
    fov_deg: 0.25,
    mjd_min: 56770,
    mjd_max: 57330,
    bands: ['W2'],
    try_next: {
      object: 'the eps Ind B field in Discover',
      params: { mode: 'discover', target: 'eps Ind B' },
      note: 'every moving candidate there is checked against bright-star artifacts like this ghost',
    },
    hide_light_curve: 'This lesson is about telling real objects from camera artifacts, not about brightness.',
    // SPIFF "New Candidates" that our check (docs/results.md, negative results) showed to be artifacts; CatWISE positions
    more_examples: {
      title: 'More impostors',
      intro: 'Real catalog "brown dwarf candidates" that turned out to be artifacts when we checked them with this app:',
      items: [
        { name: 'CWISE J201121.52-062438.1', ra: 302.83969, dec: -6.41061, reason: 'a diffraction spike of a bright star, not a source' },
        { name: 'CWISE J010458.32+124444.5', ra: 16.243, dec: 12.7457, reason: 'another diffraction spike' },
        { name: 'CWISE J010931.47-465245.8', ra: 17.38113, dec: -46.87939, reason: 'the wing of the bright star L 293-63; nothing is left once the star is subtracted' },
        { name: 'CWISE J094640.40+135550.6', ra: 146.66835, dec: 13.93074, reason: 'a streak of scattered light near IRC+10216, the brightest 5 µm source in the sky' },
        { name: 'CWISE J080741.06-344335.9', ra: 121.9211, dec: -34.72664, reason: 'a young star buried in dust: its spectrum shows ice absorption, and it does not move' },
      ],
    },
    markers: [
      { label: 'ghost (spring visits)', ra: 330.72679, dec: -56.83682, mjd: 56780.3 },
      { label: 'ghost (autumn visits)', ra: 331.01178, dec: -56.75528, mjd: 56962.0 },
      { label: 'eps Ind B (real)', ...EPS_IND_B },
    ],
    story:
      'Telescopes also create fake objects. Light from a very bright star bounces inside the optics and makes a faint out-of-focus copy, a ghost. Detectors also keep afterimages of bright stars, and cosmic rays leave single sharp hits. Here the bright star Epsilon Indi A makes a ghost in WISE W2 images.',
    look_for:
      'Next to the bright star there is a fuzzy doughnut about 5 arcminutes away. Step through the visits: every six months it jumps to the opposite side of the star (solid circle = where it is now, dashed = the other season), while the real brown dwarf (eps Ind B) stays in place.',
    quiz: {
      question: "A faint 'companion' appears 316 arcseconds from a bright star, but six months later it is on the opposite side, and then it jumps back. What is it?",
      options: ['A planet orbiting very fast', 'A reflection (optical ghost) inside the telescope, fixed to the camera, not the sky', 'A second brown dwarf', 'An asteroid'],
      answer_index: 1,
      explanation:
        "WISE flips its orientation on the sky every six months. A ghost always sits 114 detector pixels from the bright star in the same camera direction, so on the sky it swaps sides. Real objects don't care how the camera is turned. It also looks like a ring, not a point.",
    },
  },
  {
    id: 'asteroid',
    title: 'An asteroid',
    skill: 'Catch a solar-system object',
    object: '(888) Parysatis',
    ra: 5.9233,
    dec: -17.2745,
    pmra_masyr: 0,
    pmdec_masyr: 0,
    epoch_yr: 2000,
    fov_deg: 0.25,
    mjd_min: 58814.5,
    mjd_max: 58816.0,
    wise_exposures: true,
    bands: ['W2', 'W1'],
    try_next: {
      object: 'this field in Research',
      params: { mode: 'research', ra: '5.9233', dec: '-17.2745', field: '0.25', win: '58814.5,58816', exposures: '1' },
      note: 'the same exposures with the known-asteroid table and every measured number',
    },
    hide_light_curve: 'This lesson is about a fast mover inside our Solar System, not about brightness.',
    // IRSA MOST ephemeris at each NEOWISE exposure, 2019-11-27/28
    track: [
      { mjd: 58814.8503, ra: 5.87531, dec: -17.35335 },
      { mjd: 58814.9812, ra: 5.88617, dec: -17.335 },
      { mjd: 58815.112, ra: 5.89714, dec: -17.31658 },
      { mjd: 58815.2429, ra: 5.90824, dec: -17.29812 },
      { mjd: 58815.3082, ra: 5.91381, dec: -17.28886 },
      { mjd: 58815.3084, ra: 5.91383, dec: -17.28886 },
      { mjd: 58815.3737, ra: 5.91943, dec: -17.2796 },
      { mjd: 58815.4391, ra: 5.92508, dec: -17.27032 },
      { mjd: 58815.5045, ra: 5.93075, dec: -17.26102 },
      { mjd: 58815.5046, ra: 5.93076, dec: -17.26102 },
      { mjd: 58815.5699, ra: 5.93645, dec: -17.25172 },
      { mjd: 58815.7008, ra: 5.94795, dec: -17.23306 },
      { mjd: 58815.8316, ra: 5.95955, dec: -17.21436 },
    ],
    story:
      'Asteroids are so close that they move across the sky within minutes to hours. WISE took a dozen or more exposures of each spot over about a day; normally we combine them, which erases anything moving. Here every exposure of 27–28 November 2019 is shown on its own, and the main-belt asteroid (888) Parysatis, 1.7 au from Earth, crawls through.',
    look_for:
      'Play the single exposures one by one: a bright dot crawls from bottom-right to top-left along the small circles (its predicted path), about 77 arcseconds between exposures. The big circle marks where it should be in the exposure on screen.',
    quiz: {
      question: 'A dot moves ~25 arcseconds per hour within one day and is missing in all other years. What is it?',
      options: ['A nearby star with high proper motion', 'An asteroid orbiting the Sun', 'A ghost reflection', 'A variable star'],
      answer_index: 1,
      explanation:
        "Stars, even Barnard's Star, move at most ~10 arcseconds per YEAR. Moving that far in an hour means it's inside our Solar System: here the asteroid (888) Parysatis, 1.7 au from Earth.",
    },
  },
]
