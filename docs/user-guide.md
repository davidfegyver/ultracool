# User guide

This guide explains what Ultracool Browser shows and how to read it. You do not need any astronomy background.

## What you are looking at

Infrared cameras in space see heat. Three NASA missions photographed the whole sky again and again:

- WISE (2010) and NEOWISE (2014–2024) took pictures in two infrared colours, called W1 (3.4 micrometres) and W2 (4.6 micrometres), about twice a year.
- SPHEREx (2025–2026) takes pictures in 102 narrow infrared colours between 0.75 and 5 micrometres. Splitting the light like a rainbow tells us something about what an object is made of.

The app takes all the pictures of one small patch of sky (usually 3 arcminutes across, about a tenth of the Moon's width), lines them up, and plays them as a flipbook: 16 years of the same patch, oldest first.

## Why brown dwarfs

A brown dwarf sits between a planet and a star. It is too small to burn hydrogen like the Sun, so it slowly cools down. Cold brown dwarfs are almost invisible to ordinary telescopes but glow in the infrared, especially in W2. The nearby ones also drift across the sky from year to year.

## The four modes

| Mode | Use it to |
|---|---|
| Learn | take seven short lessons with real objects, each ending in a quiz. Start here. |
| Explore | type any star name or coordinates and get short answers: does it move, is it cold, does its brightness change, what kind of object is it? |
| Research | see the same answers as numbers with error bars, plus catalogues, single exposures and data export. |
| Discover | scan a wider patch of sky for everything that moves and judge each candidate yourself. |

## Reading the flipbook

Press play. Distant stars stay put. A dot that slides steadily from frame to frame is a nearby star or brown dwarf.

The pink circle marks where catalogues predict your object on each date, drawn at the size we measure it with. If the dot stays inside the circle, the object moves as expected.

Deep stacks add several years of pictures together, so faint objects rise above the noise. Turn them on when the object is too faint to see in single frames.

Blink switches between the earliest and the latest years. Anything that moved jumps back and forth.

Each picture has its own contrast, so you cannot judge brightness changes by eye. Use the light curve for that.

## The cyan probe

Drag the cyan crosshair onto any other dot in the flipbook, or right-click the sky map. Moving it does nothing by itself. When you let go, a small menu appears:

- "Measure this source" gives a quick preview in a couple of seconds. You can then ask for a full measurement (about a minute) that goes back to the original images.
- "Centre field here" makes that spot the centre of a new flipbook.

The rings around the probe show exactly which area is measured. If another star sits inside the ring, its light gets mixed in.

## What the answers mean

### Does it move?

We measure the object's position in every period and fit a straight line through them. The app only says "moves" when the motion is clear over at least two years and three separate periods. Nearby objects move by a fraction of an arcsecond up to ten arcseconds per year. An arcsecond is the width of a coin seen from 4 km away.

### Is it cold?

This compares brightness in W2 with W1 (the "W1−W2 colour"). Colder objects are much brighter in W2.

| Answer | W1−W2 | Typically |
|---|---|---|
| Normal star colours | below 0.6 | ordinary stars (and some warm brown dwarfs) |
| Red | 0.6–1.6 | L and early T brown dwarfs, or dusty stars |
| Very red | 1.6–2.6 | T brown dwarfs |
| Extremely red | 2.6 and above | the coldest brown dwarfs (late T and Y) |

### Does its brightness change?

"Regularly" means a repeating cycle, like the pulsating star in lesson 4. "Without a pattern" means irregular changes, like the young star with a dusty disk in lesson 5. WISE looked only twice a year, so some periods cannot be told apart; the app then lists the alternatives.

### What type is it?

The SPHEREx rainbow is compared with 47 reference brown dwarfs. The app gives a range of types, not a single label, because the method is good to about one or two subclasses. A type is only given when the object is clearly detected. Ordinary stars, which are warmer than any reference, are called "probably an ordinary star". If neighbouring stars spoil the measurement, the app says so instead of guessing.

## Is it real?

Cameras make fake objects: spikes and rings around bright stars, reflections ("ghosts"), afterimages and cosmic-ray hits. The app uses the missions' own artifact lists to hide most of them, but stay sceptical. Something seen on only one date, or only near a very bright star, is usually not real. Lesson 6 shows a real example.

When we checked seven "new brown dwarf" candidates from an automated catalogue, none of them was new: they were diffraction spikes, scattered light, a young star in a dust cloud, a source in another galaxy and one brown dwarf that was already known. See [results.md](results.md#what-did-not-work).

## Discover mode

Discover searches a 15-arcminute patch for everything that moves over 16 years. It uses its own detection on the W2 images and checks each candidate against image artifacts and the CatWISE catalogue. For each candidate you can play its flipbook and mark it "Real mover", "Artifact" or "Unsure". Your choices stay in your browser and can be exported. Start with the three ready-made example fields; a new field takes several minutes to prepare.

## Waiting

The first view of a new patch of sky downloads and lines up several hundred pictures, which takes a few minutes. The app shows your place in the queue and an estimate. After that the patch is stored and opens instantly for everyone.

## Limits to keep in mind

SPHEREx gives a low-resolution rainbow, not a detailed spectrum, so types are good to about one or two subclasses.

Very bright stars saturate the cameras. Their brightness then comes from the missions' catalogues instead of our own measurements.

In crowded parts of the sky, near the Milky Way, neighbouring stars blend into the measurement.

Discover does not report objects that move slower than about 0.7 arcseconds per year.

## Where the data come from

The images come from the NASA/IPAC Infrared Science Archive (WISE, NEOWISE, SPHEREx, CatWISE2020). Object names come from SIMBAD, and the brown-dwarf templates and catalogue from SPIFF (Gagné et al. 2026). [how-it-works.md](how-it-works.md) explains each step and credits the methods behind it.
