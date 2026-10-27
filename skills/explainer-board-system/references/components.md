# Components

Class names are from `assets/brand.css` (all inside `.ebs`). Motion values for each component are repeated in `motion.md`.

## Title and marker (C06: "Every board opens with one claim")
- `.title`: Inter 700, **76 px** default, line-height 1.08, letter-spacing −.035em, one line, never wraps (`white-space:nowrap`). 68 px when the line runs past ~30 characters. 60 px for short tag-titles on example boards.
- Marker on the `span`: `linear-gradient(178deg, transparent 0 50%, #DBEAFE 50% 93%, transparent 93%)`, padding 0 8 px.
- Marker sweep: left→right, background-size 0% → 100%, .6 s power2.inOut, starting .08 s after the title appears.
- Entrance: opacity 0→1, y 12→0, .4 s power3.out. On the board's first frame the title is already there.
- Write it as the claim ("Depth adds shape, not expression", "Find where the expression is lost"). The viewer should get the point of the board from the title alone.
- Don't use topic labels ("Depth", "Step 3"), two lines, or a full stop unless it is two short sentences.
- `.eyebrow`: Mono 24/1.2, `#6B7280`, caps, .07em. `.kicker`: x60 y22, Mono 22 caps .08em `#6B7280`, `em` part in `#1F2937` (section number · board name).

## Cards (C07: "Cards hold one idea each")
- `.card`: centre-aligned, padding 18 22, text 48 px Inter 700 / 1.08, border 4 ink, r3, shadow `--sh-soft`, `white-space: pre-line` for a deliberate 2-line break. A card says one thing in ≤ 6 words.

| Class | Look | Meaning |
|---|---|---|
| `.card` | plain white | problem list |
| `.card.blue` | `#EFF6FF`, blue border | a tool or model |
| `.card.mint` | `#D1FAE5` | what we keep |
| `.card.violet` | `#EDE9FE` | what we swap |
| `.card.coral` | `#FFE4E6`, coral border | problems, misses |
| `.card.accent` | `#DBEAFE` | the number |
| `.card.solid` (+tint) | r22, `0 10px 30px rgba(17,24,39,.10)` | a claim that stays ("substantial") |
| `.card.solid.ink` | blue fill, white text | the engine / answer |
| `.card.solid.code` | `#1F2937`, text `#D1FAE5`, `0 10px 30px rgba(17,24,39,.10)`, Mono 500, left aligned, padding 36 | a command or prompt the viewer can copy |
| `.card.cap` | no border, no background, 28 px | quiet caption over footage |
| `.pending` | 3 px dashed `#777`, `#F6F7F9`, Mono 38 `#555` | a missing real asset, never faked |

## Footage tile (C08: "Footage keeps its true aspect ratio")
- `.film`: border 4 ink, r8, overflow hidden, background `#1F2937`, shadow `--sh-film`; video/img `object-fit: contain`.
- **Footage is never cropped.** Every footage card shows the source's whole frame at its native aspect. Size the tile to the clip: box = clip width/height + the 4 px border.
- Don't crop footage to fill a box, stretch it, or cut off heads, hands or panel labels. No `object-fit: cover` on footage.
- Composite files (split screens, comparison renders): cut each panel out whole, panel = footage. The only crop allowed is a labelled close-up inset shown next to the full shot.
- **Caption above**: Inter 28, no box, 44 px above (`.label`). **Boxed caption** for named artefacts (mask, draft 1): `.label.box`, white, 3 px ink, height 38.
- **Tag inside** (`.film .tag`): Mono 36/1.08 (caps 28, .06em, 2 px ink border with `.caps`), top-left 14 px in, white, r3, on its word. Token tiles (`.film.token`) use a 17 px tag.
- **Focus ring**: 5 px `#DBEAFE`, inset 10 px, on a word.
- **Push-in**: video scale 1 → 1.045 over its life.
- Variants: `.film.burnfull` (no border, black, full frame), `.film.burntile` (r14, `--sh-hard-l`, tag 34).
- `.image`: border 4 `#1F2937`, white, `object-fit: contain`.
- Every board with film footage carries its credit line, for example "Footage: <title> © <owner> · used for commentary and education".

## Stickers and stamps (C09: "Stickers name it, stamps judge it")
- **Sticker** (`.sticker`): a label or a number the voice just said. Inter 700 54 px (30 for annotations, 84 for a big figure), letter-spacing −.02em, radius 20, white 5 px ring + soft drop (`--sh-sticker`), padding 0 26. Tilt −4° … +4°, alternating so neighbours never match. Fill from the sticker set; white text only on teal and blue.
- **Stamp** (`.stamp`): a verdict or status (AT THE END, TESTED, FROZEN ✕). Mono 500 caps 40 px .06em, 5 px border in the signal colour, radius 8, fill `rgba(255,255,255,.92)`, tilt −6°, padding 0 22. Verdict marks ✕ ~ ✓ are 104 px squares at 60 px; a crossed-out object gets a 110 px ✕.
- Both enter with the stamp move: scale 1.6 / rotate −6° → 1 / 0°, .3 s power4.out, on the spoken word. Both sit above tiles (z 6) and may overlap the tile they label.
- At most **5 stickers** on one board, and they arrive one per spoken word.

## Notes and arrows (C10: "A hand-drawn layer on top")
- **Note** (`.note`): Instrument Serif italic, 58 px/1.12, `#374151`. The aside: what the voice says in passing, lowercase, no full stop. **One per board**, bottom-left near x80 y914–940 or next to what it labels. Writes on left→right: `clip-path inset(-30% 100% -30% 0)` → 0, over min(1.1 s, .25 + .03 s × characters).
- **Arrow** (`svg.arrow`, full-board SVG overlay): stroke 10 px `#2563EB`, round caps; chevron head 30 px (path `M4 4 L22 15 L4 26`, 8 px). Draws on with stroke-dashoffset over min(.8, max(.2, length ÷ 900)) s, power1.out. Coral arrows point at what is missing. Curves for "goes into", straight lines for "becomes".

## Data components (C11: "Data components show the change")
- **Meter** (`.meter`): 40 px bars, 1.5 px light border, r12, label Inter 34. Grows on its word: .9 s to 100% for what is kept, .5 s to 4% for what is lost (red).
- **Layer list** (`.layers .chip`): 84 px chips, r14, 3 px `#D1D5DB`, Inter 28, number in Mono 20. Off = opacity .32. Each lights blue (`.on`: blue border, `#EFF6FF`) on its word (.3 s), 0.8 s apart when listed fast. Gap 18.
- **Sheet** (`.sheet`): Mono 28 table, r18, 1.5 px light border, `--sh-hard`, 180 px key column (+4 equal columns), key cells Mono 24 caps grey, header row `#F6F7F9`. Rows slide in x −14→0 on the word that names them.
- **What matters** (`.matters`): Mono 42/1.5 list in a solid card (r22, padding 28 36), small heading Mono 24 caps. The rejected line gets a 4 px grey strike drawn left→right (.3 s) and turns `#9CA3AF`.
- `.tbl` (generic table): r18, 1.5 px light border, `0 10px 30px rgba(17,24,39,.10)`, Mono 21/1.3, header Mono 18 caps `#6B7280` on `#F6F7F9`, `.sm` 17, `.sp` cells Inter 24.

## Questions and verdicts (C12)
- A run of attempts reads as a checklist: question card (`.qcard`, Inter 46, r22, 8 px soft shadow, padding 0 32) + a looping 160 px thumbnail of that attempt + a verdict stamp.
- Thumbnails are there from the board's first frame so the board is never title-only; each question pops on its word, its verdict slams ~1 s later.
- Verdict colours are fixed: ✕ `#E11D48`, ~ `#D97706`, ✓ `#059669`.

## Limits table (C13: "Honest limits")
- `.limits`: r22, 1.5 px light border, `--sh-hard`. One row per caveat, **118 px** tall, padding 0 32, the claim in Inter 40 on the left and a short verdict in Mono 38 on the right, coloured by signal. Rows split by 2 px `#E5E7EB`.
- The first row is there on the board's first frame; each next row slides in (x −16 → 0, .35 s) on its word and its verdict pops (scale 1.5 → 1, .3 s power4.out) when the voice gives it.
- Use this instead of a paragraph whenever the voice lists caveats, licences or "not for".

## Prompt panel (C14: "The real prompt, on screen")
- `.prompt`: black panel, r22, 4 px `#1F2937`, 10 px blue shadow, padding 26 34, Mono 21/1.38, text `#F3F4F6`.
- Header (`.ptop`): title in Inter 30 white + "MODEL PROMPT" Mono 18 caps `#9A9A94`, 2 px `#374151` rule under it.
- Syntax: 【section】 accent `#DBEAFE` · @Image1 @Video1 blue `#93C5FD` · {dialogue} green `#D1FAE5` · <sound> peach `#FECDD3`.
- It rises over a white veil (`rgba(255,255,255,.9)`); lines write in .06 s apart. It stays readable for at least **9 s**, carrying over into the next board if the voice moves on.
- Only real prompts, never invented ones: if the prompt is missing, use a `.pending` card.

## Screens and prompts (S58–S61, Y166, Y183, Y184, Y187)
- **GitHub repo screen (S58)**: shown in every video, so it is rebuilt light from the real page (owner, name, folders, About, topics, stars, forks) at phone-readable sizes. Refresh the numbers before each video. Rows slide in; Star / Fork count up. README lights on "setup guide". Cursor → Code ▾, clone panel opens, "copy this link" on "link".
- **README + setup commands (S59)**: the README's own Get started block, verbatim, in the dark code panel (Mono 22/1.62, comments grey, paths blue). Copy button flashes green on "copy". A accent bar steps line by line as the voice walks the setup; lines skipped in the voice are still shown, never edited out. The license note comes up in coral, word for word from the README, whenever FLAME or SPECTRE is mentioned.
- **Short prompt (S60, ≤ 2 lines)**: one line, big and white: composer card r26, 1.5 px light border, blue shadow, Inter 40; the pasted link as an blue chip. Verbatim. Chip drops in on "copy the GitHub link". Words appear as they are said. Key nouns get the marker; send turns black.
- **Long prompt (S61, a full page)**: the real prompt, verbatim (Mono 25). Never shrunk to fit: a fixed window scrolls to each section as it is read, a accent bar marks the lines, a fade hides the cut.
- **Live text app screen (Y166)**: a dark app mock where the current word is highlighted and the text scrolls as the line is read.
- **Prompter screen, live word (Y183)**: the current word gets an underline that moves along as the line is read.
- **Screenshot push-in (Y184)** and **Real app screen (Y187)**: the real screenshot, never cropped, slow push-in, callout cards (two on Y187) on what matters.
- **Screen recording + zoom (D55)**: real capture in a light browser frame (r18, 10 px soft shadow, address bar in Mono). Pushes in to the thing being clicked (.9 s power3.inOut), holds, pulls back. Mini-map shows where we are; a sticker names the control. Whole screenshot, true aspect; zoom with transform, never by cropping the file.
- **Terminal (D54)**: see `charts.md` (diagrams section).

## Social proof (C15, S148–S152, Y177)
- **Comment card** (`.cmt`, C15): r26, 10 px soft shadow, padding 40 44, Inter 36/1.38, avatar 96 px blue circle with initials (Inter 38). Name Inter 40, meta `#9CA3AF` 28. The sentence the voice quotes gets a marker fill (`rgba(255,225,77,.55)`) on its word; quoted words in blue.
- **Feed** (`.feedview`): scrolls once, power1.inOut, under a fade-out mask (`linear-gradient(#111827 88%, transparent)`), images r22 with soft shadow, gap 22. Feed tag `.feedtag`: blue, white Inter 30, r12, `0 10px 30px rgba(17,24,39,.10)`.
- Tools get their real logo at 1.05 em before the name (`.logo`).
- **Comment card from the comments (S148)**: a real comment rebuilt big (Inter 44), avatar as a grey circle, handle shown only with permission (otherwise "a viewer"). Pops in, then the board answers it.
- **Comment card motion (C250)**: avatar is initials, never a real face. Marked EXAMPLE unless it is a real comment.
- **Post card (S149)**: for quoting a public post (X, Threads, YouTube, LinkedIn). Rebuilt in the board style, not the platform's: name, handle, date, the text verbatim, its media at true aspect. Always link it in the description.
- **Community showcase (S150)**: their result whole, credit in Inter 40 under it, where it was made; a violet community sticker. Only with their OK.
- **Phone frame (S151)**: for 9:16 footage inside a 16:9 video. Black phone body, r56, blue soft shadow, the clip whole inside. Never crop vertical footage to fit a landscape tile.
- **Mind map (S152)**: centre topic as an ink card; branches curve out to tinted cards, one per subtopic, popping in clockwise; light the branch being discussed. ≤ 6 branches.
- **Cited stat (Y177)**: a big figure counts up, one plain line of what it means, and the source cited under it (name + link the study in the description).

## Drawn illustrations (C16: "Draw the object when there is no footage")
- Flat vector, **8 px `#1F2937` strokes**, generous radii (20–34), fills only from the palette (`#D1D5DB` metal, `#D1FAE5` the good part, `#EFF6FF` screens, `#3A3A3A` dark hardware, `#BFDBFE` one accent).
- One object per idea, side by side, each with a Inter 38 caption.
- The one that matters gets a mint glow (`drop-shadow 0 0 22px rgba(22,134,120,.55)`); the one you don't need fades to opacity .38 + grayscale; a stamp lands on each on its word.
- Never clip-art, never emoji.
- Device and gear boards (Y165, Y181): every device drawn as a line icon (or its real logo); connectors carry flowing dots and a label for what travels on them; one colour per kind of signal; a ✓ pops as each item is named; optional items say so.

## Prices and receipts (P62–P68, Y176)
- **Receipt (P62)**: paper white, soft drop shadow (`0 18px 28px rgba(0,0,0,.14)` on the AR boards), torn zigzag bottom (14 px teeth), "RECEIPT" header in spaced grey Mono over a dashed rule. Lines are Mono 26 with dotted leaders to a right-aligned amount coloured by meaning; the total is bold 34 over a dashed rule. Lines print one by one (steps, ≥ 70 chars/s) on their words. Unknown amounts are **$_.__** until the real figure is known; never guess one.
- **Price card (P63)**: white, 1.5 px light border (blue for the official list), r14, soft shadow; Mono label on top, Inter 92 number, small cents.
- **Die-cut sticker (P63)**: coloured rounded pill, rotated ±2–6°, 5 px white keyline + soft shadow like a die-cut label; condensed heavy numerals, cents small and raised. Slaps on (scale 1.5 → 1, rotate −10° → its angle, .35 s) on the word. Legend on the board: accent = cut · orange = adds · teal = under the list. [NEEDS] the condensed numeral font is not named.
- A crossed-out price gets a hand-drawn red strike that draws on before the new sticker lands.
- **Price bars + truth line (P64)**: bars sit on a 5 px ink baseline. The official price is a dashed blue line right across the chart. A seller's markup stacks on top in that seller's pastel + ink; a cut sits under the line in teal. A price nobody has published is a hatched dashed box with a "$_.__" sticker. Seller chips: pastel pill, white keyline, mascot badge, "**A** role". Companies are A / B / C unless it's their own public price.
- **Price grid + circled (P65)**: a grid of price cards (≤ 12), each slightly rotated, popping in .12 s apart. On the word, a hand-drawn red ellipse (1.2 turns, overshoots like a pen loop) circles the suspicious one and a Instrument Serif note asks the question, with a rough arrow back.
- **Recurring anchor ladder (P66)**: see `layout.md`.
- **Physical metaphors (P67)**: a gate is a brick wall, leverage is a balance that tips (back.out), banned is a big red ✕ stamp, unknown is a hatched box, a fact is a printed label (1.5 px light border, r10, Mono 24 bold, ±2°), a mechanism with no name is a stamp, a voice is a speech bubble. Humour stays flat: a crossed-out word with a label stuck over it, no zooms, no sound effects.
- **Characters + bubbles (P68)**: stick figures with a 26 px head, 6 px ink strokes, one accent prop, a Instrument Serif name in the accent colour and a Mono one-line role. Same drawing every time a character returns (seeded wobble). Speech bubble: white, 1.5 px light border, r22, tail to the speaker. Chat bubble: grey avatar, square top-left corner, never a name. Characters are fictional; questions are real ones. Cast seen: Kevin "runs an agency", Kyle "building a small product", Sam "bought the yearly plan".
- **Cost bars on one scale (Y176)**: see `charts.md`.


## Workflows and nodes (W69–W71, C245, E119, E120, Y175, Y182, Y193)
- **Node graph (W69)**: white nodes (1.5 px light border, r16, soft shadow), tinted header, a real thumbnail at true aspect, one Mono line of output. Nodes pop in left → right. Wires (6 px blue bezier) draw on. A accent token runs each wire; the node it reaches lights.
- **Editing a node (W70)**: the node gets a 6 px blue ring, its settings slide in, the changed value flips on its word with a accent flash. Rewire: a mint wire draws to the new target. Bypass: the node greys to 35 % with a stamp. Real flags only.
- **Workflow cards (W71)**: one card per recipe, side by side. Tinted header (name Inter 30 + Mono tag pill), the inputs as a chip chain (Mono 19), and the real output at its true aspect. Cards deal in .4 s apart; the one the voice recommends lifts (y −14, accent ring) and a Instrument Serif note says when to use it. 2–4 cards.
- **Node editor UI (E119)**: a full editor rebuilt big: window bar with Run, node library on the left, dotted canvas, nodes (tinted header Inter 22, output in Mono), wires with flowing dashes, an inspector, a minimap. On Run, each node rings accent in order as its stage is named; "run finished ✓" closes it. Use the real node names and settings.
- **Drag, connect, run (E120)**: the cursor grabs a node from the library (lifts with a soft shadow), drops it, drags a wire from the out-port of the step before to its in-port (the wire draws behind the cursor), then to the next step, and clicks Run: the button turns mint and every node rings. Only real nodes, one action per spoken beat.
- **Render pipeline (Y175)**: page → browser recording frame by frame → frames into an encoder → an MP4 pops out; under it, how long it takes as bars on one scale.
- **Steps on a track (Y182)**: stations on one track, each with a drawing, number, name and tool; a token travels and each station lights as it arrives; black gates = human approval. Accent = person, blue = automated.
- **Diagram workspace (Y193)**: opens on the whole map, zooms in on one part, zooms out, a hand cursor grabs and drags the canvas, then zooms on another part. Connectors flow, approval pills pulse, zoom % in the corner.

## Editors and timelines (E117–E123)
- **Edit timeline (E117)**: preview on top, a ruler in seconds, labelled tracks (V2 overlay, V1 video, A1 voice, A2 music); clips are tinted cards with their name; a coral playhead sweeps across in real time. Light the clip being explained (accent ring) while the playhead passes it. Real clip names and durations.
- **Drag onto the timeline (E118)**: the cursor picks a clip from the media bin (it lifts: scale 1.04 + soft shadow), carries it along a curve, a dashed ghost shows where it will land, a accent snap line flashes at the cut, the clip drops in; then the cursor drags its right edge to trim it to the beat. One action per beat. Real clips, true aspect in the bin.
- **Roadmap / Gantt (E121)**: see `charts.md`.
- **Drag cards onto a timeline (E122)**: steps start out of order in a tray; the cursor picks each one (lifts with a soft shadow), carries it to its slot, a accent ring shows where it will land, it drops in and a wire joins it to the step before. When all are placed the cursor hits Play and a token runs the whole line. One drag per spoken step.
- **Pan + zoom workspace (E123)**: a real workspace window bigger than the screen: the hand grabs the canvas (closed hand) and drags it, the next steps slide into view; release, grab again. Then it zooms out to show the whole thing ("zoom 30%"), and zooms back into the part that matters. The minimap shows where we are. One drag per step the voice names.

## Agents and code (A136–A141, Y167, Y168, Y170, L106, L107)
- **File anatomy (A136)**: the file in the dark code panel, lines appearing top-down; callout cards on the right point at each part and say what it does. ≤ 12 lines; scroll for longer files.
- **Folder tree (A137)**: the real folder structure, indented, folders bold, files regular; lines appear top-down; the folder that matters is coloured and gets a sticker. Real names from the repo.
- **Diff view (A138)**: removed lines on a red wash with "−", added lines on a mint wash with "+", unchanged lines plain; a sticker says the change in words. Real before/after.
- **Error → fix (A139)**: the real error in a dark panel with a red shadow; it dims when the fix (accent card, one line) lands; the success output comes in with a mint shadow. Paste real errors and real output only.
- **Stack layers (A140)**: layers stack bottom-up (compute first), widest at the bottom; each has a name and a one-line role; the layer you work in gets the sticker.
- **Decision flowchart (A141)**: questions are accent cards, answers are tinted cards; branches draw down with "yes" mint / "no" coral labels; walk the path the voice takes, lighting each step. ≤ 3 questions deep.
- **Project folder (Y167)**: the folder as a card with files branching off it, each with a one-line note of what it holds.
- **Data file + rule (Y168)**: a code panel with the key fields lit, next to the plain-language rule they trigger.
- **Checklist runbook (Y170)**: steps tick off one by one with a tool chip on each row.
- **Tool logos (L106)**: use only the logo files in the kit (`assets/claude.png`, `assets/openai.svg`), at their own colours, ≥ 40 px tall, with the tool name next to them. Don't recolour, stretch, crop, draw your own version, or put a logo on a face or on footage. Chip: logo 1.1 em + name, Inter 38, solid card (the one being talked about is blue-tinted). Tile: 130 px mark on a 300 px card for "meet the tools". vs: two chips with a black vs sticker. Codex uses the OpenAI mark (the file from this). Add any new tool by dropping its official file in the kit.
- **Agent session card (L107)**: header = real logo + name on a tint; your real prompt in a chat bubble; then the steps the agent takes, one per line, appearing as it works; a green "ready ✓" at the end. Steps are what the prompt asks for; with a real run, use its actual steps and output.

## Story beats (H142–H147, Y178, Y180, D56, D57)
- **Cold-open hook (H142)**: the first 3 seconds: the result, big, whole frame, pushing in slowly; one sticker asks the question the video answers ("how?"). No logo, no intro.
- **Agenda / chapter map (H143)**: shown once early, then returns between chapters: done chapters fade to 45 % with ✓, the current one is accent with the ring, the rest wait. Same position every time. Names = YouTube chapters.
- **Myth vs fact (H144)**: the myth as a plain card, a big red ✕ slams on it, then the fact lands in mint underneath. One pair per board, in your words from the video.
- **3 things to remember (H145)**: before the end screen: three cards, number in Mono 64, the lesson in Inter 40, dealt one per spoken point. Exactly three; words from the video.
- **Mid-roll community plug (H146)**: a 5-second card over the current board, bottom-left (clear of the camera): banner, "Join the community", "free · live calls every week", link. Slides in (.5 s), holds, slides out. Once, after the first big payoff. The board keeps running behind it.
- **Sign-off (H147)**: your mark centred (scale 0.9 → 1, back.out), one handwritten line under it. Only with the real mark file: Your channel or your channel logo.
- **Three-part anchor (Y178)**: three drawn cards light one at a time and stay as the chapter map for the rest of the video.
- **Role shift (Y180)**: two filmstrips of the same work: before, every tile is filled by hand; after, a magnifier finds the few flagged tiles and fixes them.
- **Chapter divider (D56)**: a 2–3 s beat between big parts: chapter number in Mono 220 blue rising in, the chapter name at 104 px with the marker sweep, "chapter n of m · timestamp" in Mono, progress pips (done = blue). The same names become YouTube chapters.
- **Lower third (D56)**: the first time a person appears: white card with a accent tab, name Inter 44, role Mono 22 caps, slides in from the left (.5 s power3.out), stays 4–6 s, slides out. Bottom-left, clear of the camera and the credit line.
- **Kinetic quote (D57)**: big quote mark (accent, 5 px ink outline), the sentence in Inter 96, each word coming up from 18 % to full on its spoken word, the key word getting the marker. Attribution in Mono caps. Once per video, ≤ 10 words, the speaker's own words or a real, attributed quote.

## Film workflow (F126–F130)
- **Shot breakdown (F126)**: the real shot, whole, on the left; numbered callout cards on the right with short leader lines that stop at the frame edge (never circles or marks on faces). One callout per spoken point. ≤ 4 callouts, ≤ 5 words each.
- **Failure gallery (F127)**: real failed takes side by side, each with a coral ✕ label naming the error (identity drift, frozen face, artefacts) and a mint ✓ fix; the working result lands last. Only real failures, labelled honestly.
- **Settings panel (F128)**: a big readable panel (Mono 26) with the tool's real controls: values, a slider that moves on its word, a toggle that flips. The control being discussed gets the sticker. Rebuild the tool's panel, don't screenshot tiny UI.
- **Iteration strip (F129)**: each version is a whole tile with v-number, one-word change under it, arrows between; versions deal in on their words; the final lands big below. Real versions in real order.
- **Reference stack (F130)**: each input is a tile with a boxed caption saying what it controls (movement, identity, direction, voice); lines converge into the model card (ink); the result comes out at its true aspect. Real inputs from the actual run.

## Comparisons (K122–K125, Y164, Y169)
- **Same prompt, many models (K122)**: the prompt on top in an blue panel (verbatim), then one tile per model: the real output at its true aspect, name under it. Tiles deal in .3 s apart; the winner gets the accent ring + sticker on the word. Same prompt, same settings, same seed where possible. Say what was held equal.
- **Scorecard (K123)**: rows = tools (Inter 40), columns = what matters (Mono caps). Cells are ✓ mint, ✕ coral, or a short value. Rows appear one per tool as it is named; the recommended row tints accent and gets a sticker. ≤ 4 tools × 6 criteria; every ✓ must be something you tested.
- **Blind test (K124)**: two clips side by side, whole frame, labelled only A and B; a white sticker asks the question and holds for 2–3 s; then both get stamped (original blue, AI coral) on the reveal word. Same length, same crop, synced. Credit the source.
- **Speed race (K125)**: one lane per tool; bars fill in real proportion while a seconds counter runs; the finish line is dashed ink. The winner finishes first on screen because it is faster. Use measured times; mention the hardware or plan.
- **Versus ledger (Y164)**: two named columns (blue = the new way, coral = the old way, a drawn person when one side is a human), one row per measure, revealed on its word.
- **Dot grid (Y169)**: two 100-dot grids side by side; wrong dots turn coral so the difference reads at a glance.

## Editing and audio (Y171–Y174, Y185–Y191)
- Waveform clean-up (Y171): a waveform with the gaps marked, then cut out so the clip closes up.
- Text-based edit (Y172): strike a word in the transcript and the matching clip on the timeline disappears.
- Line triage (Y173): script lines slide in; the ones that need a visual get a coloured tag.
- Audio → graphics sync (Y174): a waveform with word markers; each graphic pops exactly on its word.
- Delete words in a transcript (Y185): a selected word is removed and the timeline closes the gap.
- Trim on the timeline (Y186): a clip edge dragged by a cursor snaps to the nearest word boundary on the waveform.
- Retake detection (Y188): the spoken line on top; its attempts as code (start, end, keep, flags); the first try dims red, the retake lights mint; the same tries on a time axis below.
- Attempts map (Y189): one row per line on a real time axis; kept tries mint, dropped tries grey, partial tries hatched; then the dropped ones fade and the rule reads itself: the last try wins.
- Edit plan + progress ring (Y190): one row per line with its take and seconds chip and flags; a ring fills to how many lines are covered; missing lines sit in coral.
- Recording report card (Y191): the length shrinks from raw to rough cut; stat cards count each kind of issue; a coral health warning for audio problems.
- These Y boards carry example content ("swap in your own") and state no sizes or timings beyond the above. [NEEDS] exact values if they must be matched; read them from the board HTML.

## Panels, overlays and helpers (brand.css)
- `.veil`: full board `rgba(255,255,255,.9)`. `.wpanel`: white, 1.5 px light border, r22, `--sh-hard`.
- `.burnblack` full black; `.burnlab` insert label x40 y40, white, Mono 32 caps .06em, r4, z 5; `.i3why` "why" pill: `#DBEAFE`, Inter 34, padding 12 22, r12, `0 10px 30px rgba(17,24,39,.10)`, the "i" in blue.
- `.handle` swipe handle: 6 px lime with 1 px ink outline, 44 px lime knob (2 px ink, Inter 22 "↔"). `.dtag`: white, Mono 28/46 caps .06em, 2 px ink, r3. `.scanbar`: 12 px, `linear-gradient(90deg, transparent, #ECFDF5 12%, #fff 50%, #ECFDF5 88%, transparent)`, glow `0 0 18px 6px rgba(200,240,120,.75), 0 0 46px 14px rgba(200,240,120,.35)`, r6. `.peel`: 4 px border, r8, Mono 22 caps tag bottom-right.
- Spec / guideline helpers used on the system boards themselves (not for video boards): `.spec`, `.pin`, `.rule`, `.do` (mint `#059669` on `#F2FAF7`), `.dont` (coral `#E11D48` on `#FFF5F2`), `.swatch`, `.tick`, `.zone`.
