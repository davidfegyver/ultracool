/** Learn-mode lesson path. Each lesson pre-configures the flipbook; swap objects/windows here without touching components. */
export type Lesson = {
  id: string
  title: string
  skill: string
  object: string
  /** name for /api/resolve; or give ra/dec (deg, pm assumed 0) */
  target?: string
  ra?: number
  dec?: number
  fov_deg?: number
  mjd_min?: number
  mjd_max?: number
  /** every WISE exposure as its own frame (needs mjd window <= 30 d) */
  wise_exposures?: boolean
  bands: string[]
  /** start in deep-stack mode */
  deep?: boolean
  story: string
  look_for: string
  quiz: { question: string; options: string[]; answer_index: number; explanation: string }
  /** example object not chosen yet: show "example being prepared" instead of the flipbook */
  pending?: boolean
}

export const LESSONS: Lesson[] = [
  {
    id: 'moves',
    title: 'Something moves',
    skill: 'Spot a moving star',
    object: "Barnard's Star",
    target: "Barnard's Star",
    bands: ['W2', 'D6'],
    story:
      "Barnard's Star is a small red star only 6 light-years away, the fastest-moving star in our sky. Most stars are so far away that they look frozen in place for a lifetime, but Barnard's Star slides about 10 arcseconds every year. Over the 16 years of WISE and SPHEREx pictures, that adds up to a jump you can see by eye.",
    look_for:
      'Press play. The pink circle marks where the catalog predicts the star on each date. Watch the bright dot travel up the picture (north) together with the circle, while every other star stays put.',
    quiz: {
      question: "About how far did Barnard's Star move across the sky between 2010 and 2026?",
      options: ['Not at all: stars do not move', 'About 166 arcseconds (10.4″ per year × 16 years)', 'About one degree, twice the width of the full Moon'],
      answer_index: 1,
      explanation:
        '10.4″/yr × 16 yr ≈ 166″, close to 3 arcminutes. That is tiny on the sky (a tenth of the full Moon), but it is dozens of pixels in these images.',
    },
  },
  {
    id: 'color',
    title: 'Right color',
    skill: 'Recognize a cold brown dwarf by its infrared color',
    object: 'WISE 0855−0714',
    target: 'WISE J085510.83-071442.5',
    bands: ['W1', 'W2'],
    deep: true,
    story:
      'WISE 0855−0714 is the coldest brown dwarf known: about 250–285 kelvin, roughly the temperature of a chilly day on Earth. It was found in 2014 only 7.4 light-years away. Something that cold gives off almost no visible light, and even in the infrared it is much brighter at 4.6 µm (WISE W2) than at 3.4 µm (W1), because methane and water in its atmosphere swallow the shorter wavelengths.',
    look_for:
      'Deep stacks are on (several pictures added together, so faint things show). Switch between the W1 and W2 frames: inside the pink circle there is almost nothing in W1, but a faint dot in W2. It also moves fast, about 8″ per year.',
    quiz: {
      question: 'Why does WISE 0855 show up in W2 but almost vanish in W1?',
      options: [
        'A dust cloud hides it in W1',
        'It is so cold that it shines mainly at longer infrared wavelengths, and molecules absorb the shorter ones',
        'The W1 camera was switched off',
      ],
      answer_index: 1,
      explanation:
        'A very red W1−W2 color (W2 much brighter) is the signature of the coldest brown dwarfs (late-T and Y types). Searches for new cold worlds use exactly this color cut.',
    },
  },
  {
    id: 'together',
    title: 'Move together',
    skill: 'Find companions by common proper motion',
    object: 'Epsilon Indi A + Ba/Bb',
    target: 'eps Ind B',
    fov_deg: 0.25,
    bands: ['W2', 'D6'],
    story:
      'Epsilon Indi A is a bright orange star 12 light-years away. In 2003 astronomers noticed a faint object 402″ away moving across the sky in exactly the same direction and at the same speed, about 4.7″ per year. It is a brown dwarf, soon after found to be a tight pair (Epsilon Indi Ba and Bb), orbiting the star from far away.',
    look_for:
      'The pink circle sits on the brown-dwarf pair in the middle. The bright star near the right-hand (west) edge is Epsilon Indi A. Play the flipbook: both drift the same way by the same amount, while background stars stay still.',
    quiz: {
      question: 'Two objects 402″ apart drift the same direction at the same speed for 16 years. What does that suggest?',
      options: ['A coincidence', 'They travel through space together, likely bound to each other', 'The telescope was moving'],
      answer_index: 1,
      explanation:
        'Common proper motion is how many brown-dwarf companions are found: two random stars almost never share both direction and speed. The shared motion also tells us their distance and age come from the bright star.',
    },
  },
  {
    id: 'brightness',
    title: 'Brightness changes',
    skill: 'Read a periodic light curve',
    object: 'R Draconis',
    target: 'R Dra',
    bands: ['W1', 'W2'],
    story:
      'R Draconis is a Mira variable: an old red giant star that swells and shrinks, brightening and fading over a cycle of about 245 days. WISE looked at it twice a year for over a decade, so the light curve catches it at many different phases.',
    look_for:
      'Look at the Light curve plot below the flipbook: the W1 and W2 points go up and down by a large factor. The picture contrast is adjusted frame by frame, so brightness changes are easier to see in the plot than in the images.',
    quiz: {
      question: 'R Draconis brightens and fades over and over. About how long is one cycle?',
      options: ['About 8 hours', 'About 245 days', 'About 16 years'],
      answer_index: 1,
      explanation:
        'Mira variables pulsate with periods of 100–1000 days. Because WISE visits each spot only every ~6 months, the points sample different parts of the cycle; a period search connects them.',
    },
  },
  {
    id: 'disk',
    title: 'Dusty disk, no pattern',
    skill: 'Tell irregular variability from periodic',
    object: 'RW Aurigae',
    target: 'RW Aur',
    bands: ['W1', 'W2'],
    story:
      'RW Aurigae is a very young star, a few million years old, still surrounded by a disk of gas and dust where planets may be forming. Since 2010 it has suddenly dimmed several times for months, when clumps of dust drifted in front of it, and the hot dust glows brightly in the infrared.',
    look_for: 'Open the Light curve: the brightness jumps around with no repeating rhythm, unlike R Draconis. Compare W1 and W2: dust changes them by different amounts.',
    quiz: {
      question: "How is RW Aur's light curve different from R Dra's?",
      options: ['It never changes', 'Its changes have no regular period', 'It repeats exactly every 245 days'],
      answer_index: 1,
      explanation:
        'Young stars with disks (T Tauri stars) vary irregularly: dust, accretion and hot spots change on many time scales at once. "Variable but not periodic" is itself a clue to what kind of object it is.',
    },
  },
  {
    id: 'ghost',
    title: 'Real or ghost?',
    skill: 'Recognize image artifacts',
    object: 'Image artifacts',
    bands: ['W1', 'W2'],
    pending: true,
    story:
      "Telescopes make fake objects too. Very bright stars leave diffraction spikes and reflections (ghosts) in the optics, the detector can keep an afterimage of a bright star (a latent or persistence), and cosmic rays leave single sharp hits. The pipelines flag many of these, and the flipbook caption shows the flag names.",
    look_for: 'Find a spot that appears in only one frame or only one band, or that sits at the same place on the detector instead of on the sky. Check the caption for flags such as GHOST or PERSIST.',
    quiz: {
      question: 'A bright, sharp dot appears in one W1 frame only, not in W2 and not on any other date. What is it most likely?',
      options: ['A newly born star', 'A cosmic-ray hit or another artifact', 'A brown dwarf'],
      answer_index: 1,
      explanation: 'Real objects show up on several dates and usually in both bands. One-frame, one-band events are almost always artifacts.',
    },
  },
  {
    id: 'asteroid',
    title: 'Asteroid',
    skill: 'Catch a solar-system object',
    object: 'An asteroid',
    bands: ['W1', 'W2'],
    wise_exposures: true,
    pending: true,
    story:
      'Asteroids are so close that they move across the sky within minutes to hours. WISE took a dozen or more exposures of each spot over about a day; normally we combine them, which erases anything moving. Here every exposure is shown on its own.',
    look_for: 'Step through the exposures of one visit: one dot moves steadily from frame to frame, and it is gone in every other year.',
    quiz: {
      question: 'A dot moves across the picture within one day and is missing in all other years. What is it?',
      options: ['A brown dwarf', 'An asteroid in our solar system', 'A variable star'],
      answer_index: 1,
      explanation: 'Stars and brown dwarfs move at most arcseconds per year; asteroids move arcseconds per minute, so they appear in just one visit.',
    },
  },
]
