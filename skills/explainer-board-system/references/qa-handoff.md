# QA checks and the data handoff

## QA checks (Q34: "Check every frame before export")
| Check | Rule |
|---|---|
| bounds | Every readable element inside x60–1860, y60–1020 (arrows exempt). |
| camera-safe | Nothing in x1241–1904 × y586–1064 while the camera is on. |
| overlap | No two boxes overlap by more than 3 px unless marked `allowOverlap` (stamps on tiles, tokens, pop-ups). |
| overflow | Text never spills its box; tags never wider than their tile. |
| appears early / stays late | Nothing visible before its word or after its end (30 fps sweep). |
| empty board | At least one non-arrow element on screen on every frame. |
| media ready | Every visible video has nonzero size and is seeked to its target time (±.18 s while playing). |
| readable | ≥ max(1.5 s, .6 + words ÷ 3.2) on screen for every text element. |
| real assets only | No invented footage, prompts, stats, logos or names; missing → `.pending` card and ask. |
| credits | Every board with film footage carries its credit line (Inter 18, `#9CA3AF`, x60 y1040). |

### How to run them
1. The player exposes `window.__seek(t)` and `window.__audit()`.
2. Seek to every QA time: board start ± .04, start + .3, every element's in-time + .2, every line's midpoint, board end − .04. Run the audit at each and fix every error.
3. Run the 30 fps sweep for early, late and empty frames.
4. Screenshot each board at its first frame, its middle and its last frame, and look at them as a contact sheet before handing over.

Also check by eye: footage at true aspect and uncropped, no marks on faces, at most 5 stickers, one note, one claim title on one line, every word ≥ 28 px (≥ 36 px on 9:16), thumbnails readable at 160 px wide.

## Data schema (H35: "One JSON drives the whole video")
| Node field | Meaning |
|---|---|
| `id` · `kind` | unique id · `title` \| `card` \| `note` \| `film` \| `image` \| `path` \| `sketch` \| `html` |
| `x` `y` `w` `h` | board px, top-left box |
| `at` · `end` | in-time (word start), out-time (s, absolute) |
| `text` · `html` · `cls` | content; html for stickers, stamps, tables; extra classes (`caps`, `token`, `burnfull` …) |
| `color` | `paper` \| `blue` \| `mint` \| `violet` \| `coral` \| `accent` (card tint, arrow colour) |
| `size` · `padding` | font-size override, card padding |
| `enter` | `pop` \| `rise` \| `stamp` (default: card back.out, note write, title sweep) |
| `keys` | `[[t, {gsap vars}]]` keyframed moves: scale, x, y, boxShadow, clipPath, autoAlpha |
| `steps` | `[[selector, t, from, to]]` inner pieces (rows, chips, bars) |
| `media` · `crop` · `cropCover` | clip key, [x,y,w,h] in source px, cover vs contain |
| `clockAt` · `offset` · `loopStart`/`End` · `stop` · `rate` | video clock: plays from offset at clockAt; loops or stops |
| `freezeAt` · `freezeDuration` | pause the clip while an insert plays |
| `labelAt` · `quietCaption` | when the tile tag appears; caption without a box |
| `morphFrom` · `splitFrom` · `travel` | grow from the previous board · slide in · move along an SVG path |
| `emphasizeAt` · `collapseAt` · `contextUntil` | accent glow · collapse away · dim until |
| `z` · `allowOverlap` · `instantEntry` · `burned` | stacking · exempt from overlap QA · on from frame 1 · full-screen insert |

- **Scene**: `{id, start, end, title, nodes[], focus[]}`. Boards run back to back on the voice track; each owns its nodes.
- **Also in the file**: `MEDIA` `{key: src, width, height, duration}` · `LINES` voice lines with start/end · `CAMERA_CLIPS` camera cuts mapped to timeline time · `END`.
- Virtual camera keys: `cropXYZ` = [clip time, x, y, size] (P38).

## The agent kit (H35)
`SPEC.md` (every rule on this canvas, in words), `brand.css` (all tokens and components), `engine.js` (the GSAP player), `scene-template.json`, and the effect recipes as code. Hand an agent the kit + a transcript with word timestamps + the real footage.

**[NEEDS]** Only `brand.css` ships in the folder (copied to `assets/brand.css`). `SPEC.md`, `engine.js`, `scene-template.json` and the effect recipes as code are named on H35 but are not in `~/Downloads/Explainer-Board-System/`. Until they arrive, the player behaviour (`__seek`, `__audit`, the field names above) is a spec only. `board-sync` has its own player (`assets/player.html`, `kit.js`) that exposes `window.__seek(t)`, `window.__dur`, `window.__ready`; it does not read this schema.
