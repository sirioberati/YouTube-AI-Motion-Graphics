# Motion and animation

## Motion tokens (M30)
| Move | What changes | Duration | Ease | Used for |
|---|---|---|---|---|
| pop | y 14→0 · scale .985→1 | .38 s | power3.out | html pieces, lines, rows |
| rise | y 40→0 · scale .88→1 | .75 s | power3.out | pop-ups over the veil |
| stamp | scale 1.6→1 · rot −6°→0 | .30 s | power4.out | stickers, stamps |
| card | y 18→0 · scale .965→1 | .50 s | back.out(1.5) | cards, tiles, images |
| note write | clip-path inset L→R | .25 + .03/char, ≤ 1.1 | power1.inOut | Instrument Serif notes |
| title | y 12→0 + marker 0→100% | .40 / .60 s | power3.out / power2.inOut | titles |
| arrow draw | dashoffset len→0 | len/900, .2–.8 s | power1.out | arrows |
| move | x/y/scale keyframes | .6–.8 s | power3.inOut | tiles that travel or grow |
| spring | scale 1.3 + ring | .5 s | back.out(1.6) | point at a tile |
| collapse | scale →.05, fade | .35 s | power2.in | something that goes away |
| push-in | video scale 1→1.045 | whole life | none (linear) | every still tile |
| board in | opacity 0→1 in place | .38 s | power2.out | each new board, opaque paper |

Everything enters on its spoken word (word timestamps from the transcript). Nothing just fades unless it is a board. CSS equivalents: power3.out ≈ `cubic-bezier(.22,1,.36,1)`, back.out(1.5) ≈ `(.34,1.56,.64,1)`, power3.inOut ≈ `(.65,0,.35,1)`.

## Timing and word sync (M31: "Every element lands on its word")
- **Word sync**: an element's in-time is the start of the word that names it (from word-level timestamps), never a guess. Search for the word after the board's start.
- **Never an empty board**: something real (footage, the title) is on screen from the board's first frame; cue words get a highlight instead of a late entrance.
- **Readable**: every text element stays ≥ max(1.5 s, .6 s + words ÷ 3.2). If the board ends sooner, carry it onto the next board or bring it in earlier.
- **Clips**: at least 5–6 s of real motion; loop anything that would run out mid-board; freeze only on purpose (and say so on screen).
- **Board change**: the next board is opaque paper and fades in place (.38 s) over the last one. No slide, no double exposure.
- **Leave**: things leave by fading .28–.35 s, or by collapsing when the voice dismisses them. Pop-ups leave together with their veil.

Other timing rules stated on boards:
- Stickers arrive one per spoken word, at most 5 per board (C09).
- Prompt panels stay readable for at least 9 s (C14).
- Verdicts slam ~1 s after their question (C12).
- Content never appears before its container (C239).
- The draw of a path takes as long as the sentence that explains it (P200).
- One action per spoken beat on drag / cursor boards (E118, E120, E122, E123).
- Stagger: never more than 12 items; keep the stagger under 1.5 s total (P39).
- Lower third stays 4–6 s (D56); mid-roll card 5 s (H146); chapter divider 2–3 s (D56).
- End board: everything on screen within 1.5 s; nothing new in the last 5 s; holds ≥ 20 s (X41).

## Easing (P194: "Same move, four feels")
Pick by job: **power2.out** for arrivals (the default), **power4.inOut** for big moves across the frame, **back.out(1.7)** for pops, stickers, chips. **Never linear on UI** (linear is "robotic, avoid").
```js
tl.to(card, {x: 640, duration: .8, ease: "power2.out"}, t)
```

## Keyframes and travel (P37, P38, P39, P36)
- **Keyframe every move, never cut (P37)**: when something exists before and after a moment, it travels: one node keeps its identity and tweens between keyframes (x, y, scale, origin 0 0). Each keyframe sits on a word; between them it holds. Move: .6–.8 s power3.inOut. Spring to emphasise: back.out(1.6), .5 s. Across boards: `morphFrom`, two steps (.4 s power2.in, .4 s power2.out). Captions follow their tile. Data: `keys = [[t, {x, y, scale, duration, ease}], …]`.
- **Virtual camera (P38)**: a slow push in / pan inside the shot (the player's `cropXYZ` keys: [clip time, x, y, size]) points at a detail without circling a face. It starts and ends on the whole frame at the clip's true aspect, the tile's box never changes shape, moves are .8–1.5 s power3.inOut with holds on the words, and when the push is held the full shot sits beside it (left). Face-tracked crops (keys every .5 s) keep a moving face centred. The gentle default is the 1 → 1.045 push-in over the tile's life.
- **Stagger and collapse (P39)**: a set enters with a stagger: rise (y 40 → 0, scale .88 → 1, .75 s power3.out), .13 s apart, left to right, top to bottom. When the voice picks one, the others collapse (scale → .05 + fade, .35 s power2.in) and the chosen tile springs to the centre (back.out(1.6), scale up, accent ring), then a stamp names it.
- **Focus pull (P36)**: when the voice walks through a list, one thing is in focus at a time: the named card and its footage come to full opacity, scale 1.03 and get the 7 px marker glow; everything else drops to opacity .32 (the player's `contextUntil` / steps). The focus moves on the next word, .25 s, power3.out. A small marker tab rides the list (y keyframes, .8 s power3.inOut). Use focus pulls for 3–5 items; more than that becomes a table. Never ring a face: focus the whole tile.

## Component moves (title, cards, notes, data)
- Title: opacity 0→1, y 12→0, .4 s power3.out; marker sweep .6 s power2.inOut starting .08 s after (C06).
- Sticker / stamp: scale 1.6 / rotate −6° → 1 / 0°, .3 s power4.out on the word (C09). Price sticker slap: scale 1.5 → 1, rotate −10° → its angle, .35 s (P63).
- Note write: `clip-path inset(-30% 100% -30% 0)` → 0 over min(1.1 s, .25 + .03 s × characters) (C10).
- Arrow draw: stroke-dashoffset over min(.8, max(.2, length ÷ 900)) s, power1.out (C10).
- Meter: .9 s to 100 % (kept), .5 s to 4 % (lost) (C11). Layer chips light .3 s, 0.8 s apart (C11, E28). Sheet rows x −14 → 0 (C11). Strike-through .3 s (C11).
- Limits rows x −16 → 0, .35 s; verdict scale 1.5 → 1, .3 s power4.out (C13).
- Prompt lines write in .06 s apart (C14).
- Receipt lines print in steps at ≥ 70 chars/s (P62).
- Terminal types ~40 chars/s, steps per character (D54).

## Signature effects (E17–E29)
- **Blur teaser (E17)**: real footage of the payoff, cropped to the part that matters, with `filter: blur(16px) saturate(.6)` on the video. Scale it ~1.08 so the blur has no soft edge. A stamp promises when it pays off: "AT THE END", blue, 44 px, −6°, slammed .3 s after the tile appears. One plain line says what it is. On the payoff board the same clip plays sharp (filter → none, .9 s) and the stamp goes. Same blur for a screenshot with people who didn't agree to be on screen: blur the image itself.
- **Swipe reveal (E18)**: two clips of the same shot, same size, same clock, stacked in one tile. Top layer clip-path `inset(0 0 0 100%)` → `inset(0 0 0 0)` over 2.4 s power3.inOut on the cue line; back → 100 % over 1.6 s; settle at half → 50 % over 1.2 s and hold; the top tag pops .6 s later. Handle: 6 px lime `#ECFDF5` bar with a 1 px ink outline and a 44 px lime knob "↔", same timing (translateX). Base tag top-left, top-layer tag top-right in `.dtag`.
- **Outline wipe (E19)**: one-way swipe for "I added X". Top layer clip-path `inset(0 100% 0 0)` → `inset(0 0 0 0)` over 1.1 s power2.inOut, starting on the word. The handle travels left→right with it, then fades (.3 s). The top tag replaces the base tag when the wipe finishes. Both layers must be the same take; otherwise render a clean version first.
- **Scan and peel (E20)**: pulse the original on the word (scale 1.03, .2 s up, .3 s back). Scan: a lime scan bar (12 px, white core, lime glow 18 / 46 px) runs top → bottom in .9 s linear, revealing the landmark pass of the same shot behind it (clip-path `inset(0 0 100% 0)` → 0). Peel: two tinted copies (blue "movement", accent "identity", 4 px border, 13 % fill, Mono tag bottom-right) slide out from behind: x +38, y ∓30, rotate ∓2°, .5 s back.out(1.8). Hand-over: they shrink and fly toward the two real tiles (.4 s) as those pop in (y 18 → 0, back.out(1.5)).
- **Token travel (E21)**: a live 130 px token of each input pops (1.15), rides the arrow (~1 s power2.inOut, CSS offset-path or GSAP along an SVG path) and shrinks into the engine (.35, fade .45 s). The engine bumps 1.08 per arrival, then glows; the result rings mint as both stickers land.
- **Spring highlight and rings (E22)**: spring highlight scale 1.3 (1.45 when it is the hero) + 8 px `#DBEAFE` ring, .5 s back.out(1.6), z above its neighbours; its caption lifts with it. Settles back (.5 s power3.inOut) when the voice moves on. Meaning rings (8 px, colour = meaning) on .25 s, off .4 s. Emphasis glow on a card: `box-shadow 0 0 0 7px #ffe24a` for 2 s (.15 s in, .2 s out) on the word that names it. Never draw a circle on a face.
- **Veil pop-up (E23)**: for a side-trip without leaving the board. Veil full-frame `rgba(255,255,255,.9)`, fades in .18 s; the board underneath recedes; the camera stays on top. Panel white, 1.5 px light border, r22, 8 px soft shadow, x40 y186 · 1270×834. Content rises in: y 40 → 0, scale .88 → 1, .75 s power3.out, items 1.4 s apart; a "vs" sticker and a stamp land on their words. All of it leaves together: opacity → 0, scale .94, .35 s.
- **Full-screen insert (E24)**: the example clip with its own sound opens out of the tile it lives in. The full-frame clip starts .22 s before the cut with clip-path = the tile's rectangle (inset in px, round 8px); clip-path → `inset(0 round 0)` over .75 s power3.inOut. The voice fades out over the last .18 s before the cut; music may swell in 1.5 s early under it. The camera fades out (.25 s) and comes back .05 s after the clip (.35 s). At the end the clip fades (.35 s) and the next board is already underneath.
- **Burned-in inserts (E25)**: three ways. Black + label: the clip at its own aspect, centred on black (1440×1080 at x240), Mono 32 caps label top-left on white, fades in .35 s, scale .9 → 1. Paper + two tiles: Original vs AI from one strip, each panel cut out whole at its own aspect (r14, 10 px soft shadow, caps tags 34) on the dot paper; tiles rise y40 / scale .92, stagger .08 s; plays twice if short. Black + strip + why: a wide 1920×584 strip, label above it, and a accent "why" pill (Inter 34, r12, 6 px white shadow). Inserts are burned into the timeline: one master audio (voice up to the cut, the clip's own sound, then the voice again, music beds mixed under), and every later time shifts by the clip length. Each board under an insert keeps its clips paused (`freezeAt`) while the insert plays, and every insert is warmed 3 s early so its first frame never stutters.
- **Freeze sync (E26)**: mask, actor and result cut from one comparison render so they share a clock. The loop is timed so the mask's freeze lands on the spoken words; during the freeze the mask tile gets an 8 px red ring, a "FROZEN ✕" stamp and a coral sticker naming the cause. Ring and stamp go when the clip recovers.
- **Close-ups and zoom to fill (E27)**: when the voice points at a detail, shrink the wide tile (scale .578, origin top) and bring in a pair of close-ups cut from the full-res source and its aligned mask, same crop rect, same short loop (1.5 s on the example). Caps tags name them. Zoom to fill: the tile scales to cover the whole frame (border and radius go to 0, shadow off), .55 s power3.inOut, above everything; it drops back when the line ends.
- **Layer list + layer video (E28)**: a numbered list of stages next to one video that swipes through every layer. Chips light one by one, 0.8 s apart, in step with the video. Everything on this view enters on the same frame (no blank frame on the swap).
- **Hook: the result grows to fill (E29)**: board 1 opens on the result, whole frame at its own 16:9, under the video title. The tile is lit (accent ring) and a scribble points at it. At ~3 s the title lifts away (y −24, .5 s power2.in). .3 s later the tile grows to fill the board, keyframed from where it is (scale 1.9, origin 0 0, .8 s power3.inOut), still at its true aspect. Never a cut. The next board's tiles morph on from this frame.

## Premium motion (P194–P237)
Use the hero effects on the one hero element of a board, not on everything.
| Board | For | Recipe |
|---|---|---|
| P195 Anticipation + overshoot | the one hero element | wind-up `x:-60, .25 s power2.in`, then `x:680, .7 s back.out(1.4)` |
| P196 Kinetic type | a punchline with numbers | `from {scale:2.2, y:-30, opacity:0, blur(8px)}, .35 s back.out(2)` on its word; 1-frame shake on the big hit; numbers biggest; whole block fades together |
| P197 Mask line reveal | a statement title | SplitText lines with mask, `yPercent:110`, stagger .15, .9 s power4.inOut; soft blue marker under the key line; exit upward the same way |
| P198 Odometer roll | a payoff number | digit strips roll through 0–9 twice and land, 1.4 s power3.out, .25 s apart left to right |
| P199 Scramble decode | a code-ish name | scrambleText 1.2 s, chars `#%&@$*+=01`, revealDelay .2; Mono; seeded glyphs |
| P200 Line draw + follow | "from here to there" | drawSVG 2.4 s power2.inOut + dot on motionPath; stops pop (back.out); one path per board |
| P201 Parallax layers | a slow sideways move | far 80, mid 200, near 380 px, 4.5 s; no scale, no zoom |
| P202 3D chrome title | hook or trailer title card | CSS preview; final pass Blender (title-sequence-3d) or Three.js with 3d-metal-material; tilt rotX 18→8, rotY −10→10, 4 s sine.inOut, shine `backgroundPosition 200% 0` |
| P203 Grain, leak, glitch | finishing looks | one look per piece, low strength; grain for texture, light leak for a warm transition, glitch only on a hard cut (RGB split + slice for 6 frames); from the HyperFrames catalog (`npx hyperframes catalog grain` / `light leak` / `glitch`) or shader-dev |
| P204 Grid wave | "many of something" | `scale:0, rotation:-45, back.out(1.7), .5 s, stagger {grid:[5,10], from:"center", amount:.6}`; leave the same way |
| P205 Squash + follow-through | a stamp or sticker landing | fall `y:-420, .5 s power2.in`; squash `scaleX 1.25 / scaleY .75, .08 s yoyo`; tag swings `elastic.out(1,.3)`; shadow grows; squash under 25 % |
| P206 Liquid metal blob | slow premium accent behind one label | border-radius morph `63% 37% 41% 59%/58% 63% 37% 42%`, rotation 60, 3 s sine.inOut yoyo forever; render via registry block or threejs-shaders |
| P207 SFX timing | placing sound | pop on the exact frame the element appears; whoosh starts ~.2 s before the move and peaks as it arrives; keep SFX under the voice; never on every element; rendered by HyperFrames on the audio clock |
| P208 Shape morph | "this turns into that" | morphSVG 1.2 s power4.inOut; colour follows; label swaps as it lands; same point count on every shape |
| P209 Card flip | before / after on one card | rotationY 180, 1 s power3.inOut; one flip per idea; don't flip back unless the story does |
| P210 Iris reveal | transition from what you point at | `circle(0% at X Y)` → `circle(80% ...)`, 1.1 s power4.inOut; ring pulses at the start point; never the centre by default |
| P211 Deck fan-out | "there are N of these" | `x:(i-2.5)*150, rotation:(i-2.5)*13, origin 50% 120%, stagger .05, back.out(1.3), .8 s`; hold, gather back |
| P212 Elastic snap | "these parts fit together" | dashed empty slots first; pieces fly in `y:-300, rotation:15, x random ±260, stagger .45, elastic.out(1,.5), 1.1 s` |
| P213 Scribble highlight | "look at this word" | loop drawSVG .9 s power2.inOut on the word, arrow .5 s, then a note; only on text and numbers, never faces |
| P214 Marquee ticker | all the tools / names in a trailer | two tilted bands, opposite directions, `xPercent:-50, 14 s, linear, repeat forever`; list doubled for a seamless loop |
| P215 3D carousel | a set of options | cards at `rotationY i*45`, origin `50% 50% -420px`; ring turns `-360, 8 s power2.inOut`; the camera never moves |
| P216 Mosaic dissolve | a reveal that feels built | dark grid tiles `scale .4, opacity 0, .4 s, stagger {each:.03, from:"random"}, power3.out`; seeded order |
| P217 Live cable | two things connected while they move | bezier rebuilt from node positions every update; accent dots flow along it |
| P218 Loader → done | it runs, then it's finished | spinner `rotation 1080, 2.6 s linear`, then mint disc pops (back.out(2)), tick draws .4 s, label swaps |
| P219 Chat + typing | talking to an agent | your bubbles from the right, replies from the left after a three-dot indicator (.8 s), reply `y 20, scale .9, back.out(2)`; each bubble on the word it's quoted |
| P220 Letter wave | one emphasised word held | SplitText chars `y:-70, rotation:-6, yoyo, stagger .08, sine.inOut`; raised letter takes the accent; subtle under voice |
| P221 Confetti burst | a win moment, once per video | badge pops, 40 seeded pieces burst 1.2 s power3.out, then fall `+=260` power1.in |
| P222 Tap ripple → appear | "click this and you get that" | cursor tap `scale .82, .1 s yoyo`; 3–4 rings `scale 0→1, opacity .9→0, stagger .18, 1.6 s power3.out`; card opens as a circle from the tap point at +.4 s |
| P223 Water ripple | a fluid, dreamy moment | displacement scale 0 → 46, 2 s sine.inOut, yoyo once; never wavy while it must be read |
| P224 Focus rack | walking through items in order | others `blur(6px), opacity .4, scale .94`; the item sharp `.6 s power2.inOut`; viewfinder corners slide over; no zoom |
| P225 Spotlight | busy screen, one thing at a time | board dark except a soft round light that glides (1.2 s power3.inOut), then opens up (`--sr 520px`); the light moves, the screen doesn't |
| P226 Liquid text fill | "filling up" | outline word, two offset waves moving sideways (2 s linear forever), level eases up 5.4 s sine.inOut while a counter climbs to 100 % |
| P227 Scribble fill | colour in a chart or shape | outlines first, zig-zag marker fill per shape, drawSVG 1.4 s power2.inOut, stagger 1.2, clipped to the shape |
| P228 Cross out + rewrite | "not this, that" | red scratch drawSVG 1.6 s power1.inOut, old word to .45, new word handwritten above left to right in 2 s linear |
| P229 Hand annotations | feedback, "look here" on a screen or doc | marks draw .9 s power2.inOut, stagger 1.4; notes at +.6 s; pen colour = kind of note; never on faces |
| P230 Rotating word | "it does X, Y and Z" in a title | last word rolls up like a slot, `yPercent:-25, .7 s power4.inOut, repeatDelay 1.4`; each word its own colour; first word repeated at the end |
| P231 Type collage | energetic list in a hook or trailer | blocks slam `scale 1.6, blur(10px), .35 s back.out(1.6), each .6`; different sizes and colours; lifts away together; camera zone clear |
| P232 Tracking-in title | cinematic title card | `letterSpacing .6em, blur(18px), 2.5 s expo.out`; rule grows from the centre at +1.6 s; subtitle at +2 s |
| P233 Gooey merge | "it all comes together" | blobs drift together 3 s power3.inOut, stagger .05; goo filter blur 16 + alpha matrix 22 −9; reverse for "it splits apart" |
| P234 Shimmer + sparkle | the one thing to click, once at the end | glow `0 0 0 26px rgba(255,225,77,.35)` breathing 1.2 s yoyo; sheen sweep; four-point sparkles pop and spin, stagger .45 |
| P235 Brush stroke reveal | a loud handmade statement | fat brush paths drawSVG 2.2 s power3.inOut, stagger .12; words exist only inside the paint; exit wipes the same direction |
| P236 Scribble checklist | progress through a list | ticks .35 s, stagger 1.9; pen strike .5 s at +.3; striped progress bar fills 7.6 s linear |
| P237 Highlighter sweep | two phrases carry the point | tilted rough marker `scaleX 0→1, origin left, .8 s power3.inOut, stagger 2.6`; different colour for "before" and "after" |

## Component motion (C238–C254)
**Effect vocabulary (C238)**, the words to use in a brief. Reveals: rise, mask up, blur in, pop, wipe, flip, stagger, count. Focus: lift, glow, focus, dim others. Combine one reveal + one focus per component.
```js
tl.from(card, {y: 60, opacity: 0}, t)            // rise
  .from(card, {clipPath: "inset(100% 0 0 0)"})   // mask up
  .to(others, {opacity: .25})                    // dim others
```
| Board | Moves | Recipe values |
|---|---|---|
| C239 Price card | mask up, stagger, pop | card `inset(100% 0 0 0 round 24px), y 40, .8 s power4.inOut`; children `y 24, stagger .12` at +.5; sticker `scale 0, rotation -20, back.out(2)`. Content never before its container |
| C240 Table | wipe down, stagger, lift, dim others | rows `x -40, stagger .1`; others .3; row `#DBEAFE, scale 1.03, boxShadow 0 10px 0 #1F2937, back.out(2)`. Grows 3 %, not more |
| C241 Bar chart | draw, grow, dim others, lift, pop | see `charts.md` |
| C242 App window | draw, wipe down, dim outside, snap frame | outline drawSVG .9 s; app `inset(0 0 100% 0)` power4.inOut; veil with a hole; frame `scale 1.08, back.out(2)`; label rises under it. Same steps on a real screenshot |
| C243 Code panel | slide in, type on, line band | panel `x -120`; lines `inset(0 100% 0 0)` linear .6 s stagger .7; accent band `scaleX` from the left with a thick left marker; never more than one band |
| C244 Receipt | feed (stepped), slam stamp | paper `y -560, 4.6 s, steps(18)`; stamp `scale 2.4, rotation -14, .25 s power4.in`; line items first, total last; torn zig-zag bottom |
| C245 Node graph | pop, draw, pulse, halo, dim others | nodes `scale 0, back.out(2), stagger .3`; edges drawSVG stagger .4; accent dots on motionPath stagger .3; blue halo on the named node, others .35 |
| C246 Phone | spring in, scroll, drop + bounce | phone `y 700, rotation 8, 1.1 s back.out(1.4)`; feed `y -420, 2.4 s power2.inOut`; notification `y -140, back.out(2)`. Phone still while the screen moves |
| C247 Chips | pop, fade out, FLIP regroup | chosen accent chips travel into one row: `Flip.from(state, .9 s power3.inOut)`; others `scale .6, opacity 0` |
| C248 KPI tiles | flip, count, draw, lift, dim others | tiles `rotationX -90, origin 50% 0, stagger .3`; numbers count 1.6 s at +.4; others .35 |
| C249 Versus cards | slide in, spin, lift, grey out, pop | left `x -300`, right `x 300` at +.2; "vs" disc spins; winner `y -22, rotation -1.5, back.out(2)` + accent glow + sticker; loser `scale .94, opacity .4, grayscale` |
| C250 Comment card | blur in, read-along, beat, count | card `blur(16px), y 30`; words `opacity .12, blur(4px), stagger .28, .3 s`; heart beats; likes count up |
| C251 Folder tree | pop, grow, draw, ring, dim others, wipe open | trunk `scaleY` from top; branches `scaleX`, stagger .3; folders `x -20, stagger .3` at +.1; blue ring on one; preview wipes open beside it |
| C252 Magnifier lens | lens magnify, glide, pop | lens glides `2.6 s power3.inOut`; inner copy of the table at scale 1.9 clipped to `circle(120px)`; answer red; label pops; no camera zoom |
| C253 Card morph | morph (FLIP), crossfade, rise, fill | `Flip.from(s, 1.2 s power4.inOut)`; small label fades as it leaves; detail children `y 20, stagger .15` after landing; progress bar fills. One continuous element, never a cut |
| C254 Deal + pull one out | deal, pull out, darken pile | cards dealt `x 700, y -300, rotation 30, stagger .45, power3.out`; pick `x 560, y -40, rotation 4, zIndex 9, back.out(1.6)`; pile darkens a little |

## Footage motion (F255–F266)
Every effect ends on the whole, uncropped frame at true aspect.
| Board | For | Recipe |
|---|---|---|
| F255 Line → frame reveal | first shot of a sequence | `inset(49.6% 50% 49.6% 50%)` → `inset(49.6% 0% ...)` .5 s, then → `inset(0 round 14px)` .9 s power4.inOut; video settles 112 % → 100 % over 1.6 s |
| F256 Before / after slider | two versions, identical framing | both clips in sync; cursor drags a accent handle `--p 12%` (1.6 s power3.inOut), `88%` (1.6 s), `50%` (1.2 s); top clip `inset(0 0 0 var(--p))` |
| F257 Video wall → hero | "all the versions, this is the one" | clips pop in a diagonal wave `scale .5, rotation -6, stagger {grid:[2,4], amount .8}, back.out(1.6)`; others `blur(6px) grayscale(1), opacity .3`; hero travels and grows (scale 2.05, power4.inOut); sticker names it; the element grows, no camera zoom |
| F258 Full frame → corner + list | "watch this, now here's why" | clip `scale .42, origin 100% 0, 1.2 s power4.inOut` into the top-right (still playing, whole); points `x -40, stagger .6` at +1 s. Reverse to go back |
| F259 Film strip → pick one | stages or takes in order | strip slides `x -420, 3.6 s power3.inOut` (sprocket holes); pick lifts `y 290, scale 1.2, back.out(1.4)`; others .35 |
| F260 Frosted glass caption | text over footage | `.glass {backdrop-filter: blur(18px) saturate(1.4); background: rgba(255,255,255,.18)}`; glass rises `y 120, .8 s`; words `opacity 0, y 14, blur(6px), stagger .2`; off faces, centred low |
| F261 Exploded footage layers | "this shot is made of layers" | stack turns `rotationY -38, rotationX 14, 2.6 s power3.inOut`; layers `z (i-2)*120`; labels stagger .3 at +2.2; collapse back flat; the stack turns, the camera doesn't |
| F262 Cinematic open | opening a film clip | black bars part `yPercent ∓100, 2 s power4.inOut`; title tracks in `letterSpacing .5em, blur(14px), 2 s` at +1.6 |
| F263 Iris: draft → final | v1 → final on the same shot | final opens `circle(0% at 14% 82%)` → `circle(130% ...)` 1.8 s power4.inOut from a corner away from the face; accent ring pulses; label swaps |
| F264 Clip in a laptop | "what you get on your computer" | drawn laptop `y 560, rotationX 30, 1.2 s back.out(1.3)`, clip already playing; glare `xPercent -120 → 320, 2 s sine.inOut` at +1.6, once |
| F265 Tiles assemble the clip | "put together from parts" | 4 × 3 grid of the playing clip flies in from seeded random places `x ±500, y ±400, rotation ±40, scale .7, stagger {each .06, from random}, 1.4 s power3.out`; scatters again on exit |
| F266 Text knockout → full clip | a hook title made of footage | `.knock {background:#0E0F12; mix-blend-mode:multiply}`, white letters show the video; word `scale 3.2, 1.4 s power4.in`; layer fades .8 s at +.9 |

Footage also: push-in 1 → 1.045 on every still tile (C08, M30); cold-open result pushing in slowly (H142).

## Diagram motion summary
See `charts.md` for every chart and diagram build (bars, line, donut, pyramid, cycle, funnel, timeline, venn, matrix, tree, steps, terminal, waterfall, stacked, grouped, slope, dot plot, KPI, ranking, gauge, heatmap, Gantt).

## The 12 s preview loops
On the reference boards every effect loops (12 s CSS loops with inline `animation-delay`) so you can see its timing. The real video does not loop boards: each element is placed on its word by the player. The CSS loop keyframes differ slightly between board families (see `conflicts.md`); use the token table above for the real values.
