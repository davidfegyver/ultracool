# Ultracool Browser: a plain-language guide

This guide explains what the app shows and how to read it, without assuming any astronomy background.

## What you are looking at

Infrared cameras in space see heat. Three NASA missions photographed the whole sky again and again:

- **WISE** (2010) and **NEOWISE** (2014–2024): two infrared "colours", called **W1** (3.4 micrometres) and **W2** (4.6 micrometres), about twice a year.
- **SPHEREx** (2025–2026): 102 narrow infrared colours between 0.75 and 5 micrometres. It splits light into a rainbow, so it can tell what an object is made of.

The app takes all those pictures of one small patch of sky (usually 3 arcminutes across, about a tenth of the Moon's width), lines them up, and plays them as a **flipbook**: 16 years of the same patch, oldest first.

## Why brown dwarfs

A **brown dwarf** is an object between a planet and a star: too small to burn like the Sun, so it slowly cools down. Cold brown dwarfs are almost invisible to ordinary telescopes but glow in the infrared, especially in W2. The nearby ones also drift across the sky year by year. That's what this app is built to see.

## The four modes

| Mode | Use it to |
|---|---|
| **Learn** | Take seven short lessons with real objects, each ending in a quiz. Start here. |
| **Explore** | Type any star name or coordinates and get plain-English answers: does it move, is it cold, does its brightness change, what kind of object is it? |
| **Research** | See the same answers as numbers with error bars, plus catalogues, single exposures and data export. |
| **Discover** | Scan a wider patch of sky for everything that moves and judge each candidate yourself. |

## Reading the flipbook

- **Press play.** Distant stars stay put. A dot that slides steadily from frame to frame is a nearby star or brown dwarf.
- **The pink circle** marks where catalogues predict your object on each date, drawn at the size we measure it with. If the dot stays inside the circle, the object moves exactly as expected.
- **Deep stacks** add several years of pictures together, so faint objects rise above the noise. Turn this on when the object is too faint to see in single frames.
- **Blink** switches between the earliest and latest years. Anything that moved jumps back and forth.
- **Each picture has its own contrast**, so you can't judge brightness changes by eye. Use the light curve for that.

## The cyan probe: measuring anything else

Drag the cyan crosshair onto any other dot in the flipbook (or right-click the sky map). Moving it does nothing by itself. When you let go, a small menu appears:

- **Measure this source**: a quick preview in a couple of seconds, then optionally a **full measurement** (about a minute) that uses the original images.
- **Centre field here**: makes that spot the centre of a new flipbook.

The rings around the probe show exactly which area is measured. If another star sits inside the ring, its light gets mixed in.

## What the answers mean

**Does it move?** We measure the object's position in every period and fit a straight line. "Moves" is only said when the motion is clear over at least two years and three separate periods. Nearby objects move by a fraction of an arcsecond to ten arcseconds per year (an arcsecond is the width of a coin seen from 4 km away).

**Is it cold?** Compares brightness in W2 with W1 (the "W1−W2 colour"):

| Answer | W1−W2 | Typically |
|---|---|---|
| Normal star colours | below 0.6 | ordinary stars (and some warm brown dwarfs) |
| Red | 0.6–1.6 | L and early T brown dwarfs, or dusty stars |
| Very red | 1.6–2.6 | T brown dwarfs |
| Extremely red | 2.6 and above | the coldest brown dwarfs (late T and Y) |

**Does its brightness change?** "Regularly" means a repeating cycle (like the pulsating star in lesson 4); "without a pattern" means irregular changes (like the young star with a dusty disk in lesson 5). WISE looked only twice a year, so some periods can't be told apart: the app lists the alternatives.

**What type is it?** The SPHEREx rainbow is compared with 47 reference brown dwarfs. A type is only given when the object is clearly detected. Ordinary stars, which are warmer than any reference, are called "probably an ordinary star". If neighbouring stars spoil the measurement, the app says so instead of guessing.

## Real or ghost?

Cameras make fake objects: spikes and rings around bright stars, reflections ("ghosts"), afterimages and cosmic-ray hits. The app uses the missions' own artifact lists to hide most of them, but stay sceptical: something seen on only one date, or only near a very bright star, is usually not real. Lesson 6 shows a real example.

## Discover mode

Discover searches a 15-arcminute patch for everything that moves over 16 years, using its own detection on the W2 images, and checks each candidate against image artifacts and the CatWISE catalogue. For each candidate you can play its flipbook and mark it **Real mover**, **Artifact** or **Unsure**; your choices stay in your browser and can be exported. Start with the three ready-made example fields; a new field takes several minutes to prepare.

## Waiting

The first view of a new patch of sky downloads and lines up several hundred pictures, which takes a few minutes. The app shows your place in line and an estimate. After that the patch is stored and opens instantly for everyone.

## Limits to keep in mind

- SPHEREx gives a low-resolution rainbow, not a detailed spectrum: types are good to about one or two subclasses.
- Very bright stars saturate the cameras: their brightness then comes from the missions' catalogues instead of our own measurements.
- In crowded parts of the sky (near the Milky Way), neighbouring stars blend into the measurement.
- Objects moving slower than about 0.7 arcseconds per year are not reported as movers in Discover.

## Where the data come from

NASA/IPAC Infrared Science Archive (WISE, NEOWISE, SPHEREx, CatWISE2020), SIMBAD, and the SPIFF brown-dwarf templates and catalogue (Gagné et al. 2026). See the [README](../README.md) for full credits and technical details.
