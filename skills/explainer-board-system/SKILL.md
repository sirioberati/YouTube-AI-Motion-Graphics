---
name: explainer-board-system
description: The look, layout and motion system for 16:9 YouTube explainer boards, in the "Clean minimal" starter theme (white paper, thin-bordered cards with one soft shadow, Inter / JetBrains Mono / Instrument Serif, one blue accent, footage tiles at true aspect, camera box bottom-right). Use whenever you design, build, review or animate an explainer board, slide, chart, diagram or end screen; when someone asks for the board colours, fonts, sizes, safe zones, camera keep-out, chart rules, motion, easings or word-sync rules; when choosing which board fits a line ("which board for a price breakdown?"); or when QA-checking boards before export. It owns how boards look and move; explainer-board-brief owns what goes on them.
---

# Explainer Board System ("Clean minimal" starter theme)

The look, layout and motion system behind the 74 starter boards in this repo (`boards/`), each a live 1920×1080 HTML page. Make it yours: change `references/tokens.md` and `assets/brand.css`, and add every correction you make to `checks.md` at the repo root.

## Who owns what

| Skill | Owns |
|---|---|
| `explainer-board-brief` | What goes on each board: which script lines need a board, the words, numbers and examples. |
| **`explainer-board-system`** (this) | How a board looks and moves: tokens, layout, components, charts, motion, word-sync rules, QA checks, which board fits which line. |
| `board-sync` | Syncing the boards to the final audio, rendering the board track, its own QA report. |

## Non-negotiables

1. **Real assets and data only.** No invented footage, prompts, stats, logos or names. Illustrative content is marked EXAMPLE. A missing real asset becomes a dashed `.pending` card, never faked.
2. **Footage keeps its true aspect, never cropped.** No `object-fit: cover` on footage. Change the layout to fit the footage.
3. **Camera keep-out stays clear.** Camera box x1400 y704 · 480×336 (or your own numbers). Nothing readable in it while the camera is on.
4. **Phone-readable text.** Every readable word at 28 px or more.
5. **No marks on faces.** Ring the whole tile, or cut a close-up.
6. **Motion comes from the elements, not camera zooms.**
7. **Everything enters on its spoken word** (word timestamps).
8. **Never an empty board.** Something real is on screen from the first frame.
9. **One claim per board**, written as the title. One idea per card, 6 words or fewer.
10. **Nothing sits still for more than 5 seconds.**

## How to use this skill

1. Get the content from the brief (`explainer-board-brief`). No brief: ask what the board must make the viewer understand.
2. Pick the board for the line: `references/board-catalog.md` (each board with **say it when** tags in spoken words).
3. Lay it out: `references/layout.md`.
4. Build from `references/tokens.md`, `references/components.md` and `assets/brand.css` (root `<div class="ebs">`, every element absolutely placed in board pixels).
5. Charts and diagrams: `references/charts.md`. Motion: `references/motion.md`.
6. Check it: `references/qa-handoff.md`, `references/do-dont.md`, and the repo's `checks.md`.

## Reference files

| File | What is in it |
|---|---|
| `references/tokens.md` | Colours, type scale, shape, shadow, easings |
| `references/layout.md` | Canvas, margins, title zone, camera keep-out, layout patterns, 9:16, end screen |
| `references/components.md` | Titles, cards, footage tiles, stickers, stamps, notes, arrows, data, verdicts, prompt panels, screens, nodes, code |
| `references/charts.md` | Bar, line, donut, pyramid, cycle, funnel, timeline, venn, matrix, tree, steps, waterfall, stacked, slope, scatter, KPI, ranking, gauge, heatmap |
| `references/motion.md` | Motion tokens, word sync, easing, signature and premium effects with GSAP recipes |
| `references/board-catalog.md` | The 74 boards, what each is for, when to use it, and which to keep when two do the same job |
| `references/qa-handoff.md` | QA checks and the data schema |
| `references/do-dont.md` | Every do and don't in one list |
| `assets/brand.css` | The stylesheet |

Some references mention boards that are not in this starter set (codes like `E27`, `F255`). Treat those as descriptions of the move; build them from the recipe.
