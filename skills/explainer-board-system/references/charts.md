# Charts, data and diagrams

General rules across the chart boards:
- Real numbers only, with the date they were taken (C113) or the source named (Y177). Illustrative values carry "example data · replace with real numbers" and the EXAMPLE tag.
- Start the axis at 0. One unit per chart (D43). Gridlines 2 px dashed `#E5E7EB`, axis labels in Mono (D43, D44).
- One colour per tool, the same colours as the tools' chips everywhere in the video (C110).
- Build on the words: each bar, segment, stage or point lands on the word that names it.
- Focus after build: on the key word the others dim (opacity .3–.35, often grayscale), the hero lifts or gets the accent ring, a sticker names the takeaway.
- Scores out of 10 need a stated source or "my score" (C110). Positions must come from real tests or be tagged "my read" (C112). Say how a score or reading was made (C114, C115).

## Bar chart (D43)
- Bars 110 px wide, 1.5 px light border (no bottom), r10 top, blue; the one the voice is about is mint + 8 px accent ring. Baseline 1.5 px light border.
- Each bar grows scaleY 0 → 1 from its base, .6 s power3.out, .15 s apart, on the word that starts the comparison; values pop above each bar .45 s later; the takeaway lands as a sticker ("8× cheaper").
- ≤ 8 bars. One unit. Start the axis at 0.

## Chart build + focus bar (C241)
The axis draws, bars grow from the baseline with a stagger; on the key word every other bar goes grey and dims, the hero bar lifts, and a callout pops with a drawn leader line.
```js
tl.from(axis, {scaleX: 0, transformOrigin: "0 50%"}, t)
  .from(bars, {scaleY: 0, transformOrigin: "50% 100%", stagger: .1})
  .to(others, {filter: "grayscale(1)", opacity: .35}, wordT)
  .to(hero, {y: -12, ease: "back.out(2)"}, wordT)
```

## Line chart (D44)
- Line 10 px blue, round joins, draws on with stroke-dashoffset over ~3 s (power2.inOut) while the voice tells the story left to right; a accent 30 px dot rides the head of the line (offset-path). The area under it fades to 18 % blue at the end.
- Mark the turning point with a white sticker + short arrow on the word that explains it. Gridlines dashed, labels Mono, axis from 0.

## Donut and big number (D45)
- Donut: 64 px ring, track `#EFF6FF`, value blue, 1.5 px light border outlines; fills clockwise from 12 o'clock (1.6 s power3.out) while the centre number counts up with it.
- Big number: Inter 200 px, −.05em, counts up from 0 on its word (1.4 s); the unit under it in Mono caps. Two numbers compared stack with a "vs" sticker; the bad one is coral.
- Counters: CSS `@property` integer or GSAP innerText with snap 1. (The A boards declare `@property --num <integer>` with `.cnt::after{content: var(--pre) counter(n) var(--suf)}`.)

## Pyramid (D46)
For anything that builds up. Trapezoid layers with 5 px ink outlines in the card tints; the base enters first and each layer drops on top (y −60 → 0, back.out(1.5)) .5 s apart, on its word, label centred (Inter 34), index in Mono at the right edge. The layer that matters (usually the top) gets the marker glow. 3–6 layers.

## Cycle / loop (D47)
For any repeating process. 3–6 stage cards (solid, r22, tinted) on a dashed blue track; a accent token orbits (offset-path on the circle, constant speed) and each stage lights (scale 1.08 + accent ring) as the token reaches it. Time the orbit so each stage lights on its word. The centre names the loop in Inter 52; a Instrument Serif note says how often it turns. The track drifts slowly (one turn / 40 s) so the board is never still. Clockwise, first stage at 12 o'clock.

## Funnel (D48)
For anything that narrows. Trapezoid stages, 5 px ink, tints getting warmer toward the bottom; each stage opens from the centre (scaleX .6 → 1, .5 s power3.out) .6 s apart on its word; the count pops at its right edge (Inter 52). The last stage is accent: it is the answer. 3–5 stages.

## Timeline (D49)
For history and sequence. An 8 px ink line draws left → right over the voice's sweep; milestones (36 px dots, 5 px ink) pop as the line reaches them, with a solid card above or below, alternating so labels never collide. Year in Mono 24, name in Inter 30. Today's milestone is accent with a coral "NOW". Space milestones by real time, not evenly. ≤ 7 milestones. Check every date before you ship.

## Venn (D50)
For overlap. Two (or three) circles slide in from the sides (x ∓160 → 0, .6 s power3.out), 8 px strokes, 14–18 % fills of their colour. A white sticker slams into the intersection on its word. Labels inside each circle away from the overlap. Use only when the overlap is the message.

## 2×2 matrix (D51)
For trade-offs. Axes draw from the centre (6 px ink), Mono axis names with arrows. Options drop into their quadrants as solid cards, one per word. The answer starts where people expect it, then travels (keyframes, back.out) into the winning quadrant and gets the accent ring; a sticker names the quadrant.

## Tree (D52)
For breakdowns. Root on top (ink card), children below; branches are 6 px curves that draw down (.4 s) before each child pops. Grandchildren use plain cards and thinner blue branches. ≤ 3 levels, ≤ 4 children per node. Shallow, wide trees keep the camera zone empty.

## Numbered steps (D53)
For how-to sequences. Numbered 120 px circles on a progress rail; the rail fills blue as the voice moves through the steps and each number lights (blue fill, white numeral, scale 1.08, back.out) when reached; its card rises in below. 3–6 steps, each ≤ 5 words. A step with a command becomes a code card.

## Terminal (D54)
Panel `#151517`, 1.5 px light border, r22, 10 px blue shadow, three grey dots, Mono 30/1.6. The path is blue, the $ accent; the command types (steps per character, ~40 chars/s) after a blinking accent cursor; output lines appear one by one in green; a stamp confirms. Only real commands and real output. Long output scrolls; never shrink the type below 26 px.

## Waterfall (C108)
For anything built up or broken down (price, cost, time). The first bar starts at 0 (blue); each step floats from where the last ended, coral when it adds, mint when it cuts, joined by dashed connectors; the total is ink and sits on 0 again. Bars grow .5 s, .7 s apart, each on its word; the value pops above with its sign. 3–7 steps.

## Stacked bars (C109)
For totals made of parts. Each bar stacks its parts bottom-up in the same order and colours (legend above, one colour per part); the total on top in Inter 34. Segments grow one after another. ≤ 4 parts. Light the part the voice is about; drop the others to 30 %.

## Grouped bars (C110)
For several things compared on several criteria. One group per criterion, one colour per tool. Groups grow left → right as each criterion is named; a sticker lands on the winner of the criterion being discussed. ≤ 4 tools × 5 criteria.

## Slope chart (C111)
For change between two moments. Two ink posts; each item is one line from its old value to its new one, drawn on (.8 s) one at a time, dots at both ends, labels at the ends in the item colour. Clearer than two bar charts when the point is who moved and how much. ≤ 6 lines.

## Dot plot / scatter (C112)
For two qualities at once. Each tool is a 60 px dot with its letter, popping in on its name; the winning region is tinted and named; the answer gets the accent ring. Say which way is better on each axis.

## KPI row + sparklines (C113, C248)
- One card per number: Mono label, Inter 110 value that counts up on its word, a 7-point sparkline drawing on under it in the same colour. 2–4 cards. Real numbers only, with the date taken.
- Motion version (C248): tiles flip down from their top edge one after another; each number counts while its sparkline draws; the tile that matters lifts with a soft colour halo and the other three dim.

## Ranking table (C114)
For a verdict across many tools. Rows reveal from last to first (.5 s apart) so the winner lands last; rank badge, name Inter 42, a score bar in the tool's colour, score on the right. Winner row accent-tinted with the ring. ≤ 6 rows.

## Table cascade + row focus (C240)
The table wipes down, rows slide in one by one; when the voice names the answer, that row turns accent and lifts while every other row dims. The row grows by 3 %, not more.

## Gauge + progress (C115)
Gauge for a judgement on a scale: three zones (coral / accent / mint), the needle swings in with overshoot (back.out) while the number counts up. Progress bar for "how far along": blue fill + % + a checklist that ticks.

## Heatmap / calendar (C116)
For activity over time. A 7 × N grid of rounded cells, 5 shades of blue, legend below ("less … more"); cells fill week by week left → right. A sticker names the week that matters. Use real logs.

## Share split (Y163)
The job as 10 tiles: a helper fills its share tile by tile while a counter climbs, then a drawn person takes the last part and checks it. Change the split by changing how many tiles fill.

## Cost bars on one scale (Y176)
One bar per option on the same dollar scale; ranges are hatched; the saving is bracketed between bars. A drawn person marks the human option.

## Bars vs a threshold (Y192)
One bar per item, a dashed limit line; bars over the limit turn coral.

## Effective hourly (Y179)
Two bars of earnings per hour worked; the taller one wins without changing the price.

## Cost calculator (B131)
Inputs as big fields (Mono 28 labels, Inter 34 values), an equals sign, the total counting up in coral, and the formula written out under it so the viewer can redo it. Real prices with the date checked.

## Unit economics (B132)
One horizontal bar = the price; segments grow left → right (cost coral, time violet, margin mint), each with its value; the price line under it and a sticker with the margin.

## Market map (B133)
One column per category (coloured header), chips for each player (A/B/C, or real names only when quoting their public info). Columns deal left → right; light the column being discussed. Money flows right → left on the example board.

## Request → response (B134)
App card → the request (dark code panel, method in accent, keys in blue) → model card (ink); the response comes back below in a mint-shadowed panel ("200 OK") along a mint path to the app. Keep JSON to 4–6 lines; real field names when you show a real API.

## Document highlight (B135)
The page rebuilt big (Inter 28/1.7); the marker sweeps under each line as it is read; red Instrument Serif margin notes say what it means. Quote the real text verbatim and name the document.

## Roadmap / Gantt (E121)
Rows are tasks (Inter 28), columns are weeks; each task is a tinted bar that grows from its start to its end (.5 s apart); a coral "today" line. The final milestone is solid blue. ≤ 8 rows. Overlap shows what runs in parallel.

## Price bars, price grid, ladder (P64, P65, P66)
See `components.md` (prices and receipts).
