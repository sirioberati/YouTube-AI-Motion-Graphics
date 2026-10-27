# The rules for board animation, and where board-sync enforces each one

Every rule below comes from real reviews of earlier board videos. The quotes are the presenter's words. Each rule names
the code that enforces it, so a trainee (or a later agent) can check the behaviour instead of trusting it.

The rules run in this order inside `scripts/choreo.py` (`Board.run`): structure, anchors, timing limits, names and
containers, money vs count, fillers and notes, nothing moves after landing, reading order, copy flags, uncovered speech.

---

## 1. No board opens empty

> "WHY IS THIS EMPTY WHEN IT STARTS"

- The headline (and a small header label above it, if the board has one) is on screen from the first frame. It is
  never hidden and never animated in (`move: "label"`).
- Structure lands first: containers, zones, outlines, rails and chart baselines cascade in from 0.45 s, 0.12 s apart
  (`Board.run`, the `structure` list; the brief's `structure as the board opens: …` build feeds it). A box the brief
  put in the structure brings its unnamed holders and its textless parts with it. Numbers the brief marks
  `(…, recalled)` join this cascade too.
- The first content item is on screen by 0.9 s. If nothing has landed by then, the first textless structure (boxes,
  panels, icons, rails) that the brief did not tie to a word is pulled into the opening cascade (`Board._opening`).
  If every element on the board is a named thing, the board opens with its headline and the report says
  "opens with the headline only until X s": named things still wait for their name (rule 4 wins).
- A board under 5 s gets its whole structure and its labels inside the first second (`Board._opening`, `short`).
- A container's own outline and strokes (the hand-drawn box around a card, a drawing inside it) come 0.1 s after the
  container, wherever the container lands; in the opening cascade they open with it, never later with the content
  (`Board._follow`).
- A full-frame panel behind everything (a dark board) is part of the paper: on screen from the first frame.
- Honesty tags at the bottom (SEEN, EXAMPLE, MY READ, SIMPLIFIED) are on screen at 0.25 s.

## 2. Named things appear when they are named

> "I say this is kyle and you do not even show kyle"

- Every build in the brief lands on its anchor words: the first time the verbatim phrase is spoken inside the
  board's window, t = word start + 0.05 s (`Board.locate`). The search is tolerant of punctuation, "$9 .40" style
  splits, number words ("five thousand dollars" = "$5,000", "half a million" = 500,000) and short ad-libs between
  the anchor words ("it's three" still finds "it's going to be three").
- Inside a matched phrase the element lands on the word that names it, not on the phrase's first word
  ("This is Kevin" lands Kevin on "Kevin").
- Builds are searched in their order: each phrase is looked for from the previous build's landing word on (so a
  repeated "$10" or "AI APIs" lands on the right mention), and only then anywhere in the window.
- If the phrase is not heard (or the build has no anchor words): the element's own text, then the build's key
  number, then the element cascades 0.2 s after the previous one. Each of these is an "anchor not found" flag in the
  cue file and the QA report. Nothing is ever hidden silently, and a missing anchor never stops the run.
- A part never appears without its container: a part lands at least 0.1 s after the box that holds it; if the brief
  anchored only the part, the box is pulled to 0.1 s before it (`Board._containment`). An arrow never lands before
  both of the things it connects (`Board._ends`; another stroke never counts as an end). When its anchor words come
  before one of its ends exists, it lands with the later end and the cue file gets the flag
  `arrow waits for <end> (anchor '<words>' at X s, lands at Y s)`; a wait over 2 s is also in the report, so the
  brief writer can move the anchor.

## 3. Every element animates, and lands on the voice

> "why is the app not even animated? why are you animating things half ass?"

- Every element of the board gets its own move from its kind (`units.py` `DEFAULT_MOVE`; `assets/kit.js`): receipt
  rows wipe in, bars grow from their base, stickers pop (from 0.82), handwriting writes on, strokes and arrows draw
  along their path, boxes and labels rise.
- Never before the word, never more than 2 s after it (`Board.run`, the rule-3 clamp). A `with:` chain lands 0.1 s
  after its target. Several elements on one anchor land 0.1 s apart in the order the brief lists them.
- Video inside a board (an app recording) plays frame-accurately: the scene seeks the video with the timeline
  instead of letting it run on its own clock (`kit.js` `syncVideos`).
- QA proves it from the real frames: each element must be absent 0.1 s before its landing and present 0.5 s after.

## 4. Money is not a count

> "I am saying 5 out of 13 and why are you having 13$ pop up? other things pop up randomly"

- A stamp (1.5x then settle in 0.45 s; capped at 1.22x when the number is over 70 px) only happens on a number whose
  role in the brief is money or percent, and only when the spoken token is said as money or percent: it carries $,
  dollars, bucks, % or percent, or follows pay / costs / at / is / about / list. Never after "of" or "out", never
  before different / sellers / prices / versions / seconds / minutes / lines / apps / clips (`money_ok`,
  `Board._stamps`).
- One stamp per element, on the element that landed on that mention; never a "reveal" stamp that is not tied to a
  spoken number. A count ("5 of 13 (count)" in the brief) never stamps.
- A number written `(…, recalled)` in the brief, and anything listed in the structure step, is context: it comes in
  with the structure cascade and never stamps (`Board._recalled_tokens`, `context_ids`).
- The fix for a wrong stamp is the number's role in brief.md, never the board.

## 5. Fill the white space while the presenter talks

> "you can add things if you think there's too much white space"

- Nothing sits static for more than 3 s while the presenter talks (`Board._notes`), and never more than 4 s while any of
  the presenter's words are available: if a stretch stays over 4 s (no free space on a full board), the report says why.
- The brief lists build steps and fillers only for gaps over about 8 s. Its fillers go first, each on its own anchor
  words, in its own style (hand, sticker, tag, mono, stamp), placed near the element it names when it says
  "near …".
- board-sync itself fills every other stretch of 3 to 8 s of dead air, and any longer gap the brief missed, with auto
  notes in the presenter's exact words: a phrase of 2 to 4 of the presenter's words around a number or a 5+ letter word that is not already
  on the board, in the hand style.
- Brief fillers take precedence in their window: an auto note keeps 2.6 s clear of every brief filler (less when two
  fillers are closer than that allows, and at the very least 1.3 s when it is the only way to keep a stretch under
  4 s). Fillers are never counted as the board's design text (they do not block an auto note's words and do not count
  as board copy for the copy checks).
- Auto notes prefer the strongest spoken words (numbers, distinctive 5+ letter words not on the board); when none are said in
  the stretch, any short phrase of the presenter's words is used, shortened to fit the free space.
- Brief fillers: at most max(16, one per 4 s of the board); fillers plus auto notes: at most one per 2 s. Never in the
  camera zone (bottom-right 615 x 430 px, 40 px in from the edges; a filler asked to sit near something in the zone is
  placed outside it and reported) and never above or beside the headline. On a dark board notes use light ink. A note fades when something lands on its spot or after 9 s; when
  space runs out, a note that has been up for 2.5 s gives its place to the new one.

## 6. Bigger, not closer

> "maybe not zoom, make the stickers bigger, or something"

- No zooms, push-ins, camera moves or leans. Emphasis comes from size: notes are placed in the largest free area at
  that moment and sized by how full the board is (130/96 px under 15 % coverage, 84/64 px under 40 %, else 54 px);
  money numbers stamp at 1.5x.

## 7. Nothing moves after it lands

- No pulses, nudges, bobs, loops or second mentions. Every tween ends in the element's resting state; there are no
  repeats or yoyos in `kit.js`. The headline's highlighted word pops once, on its word. A stamp is the only move on
  an element that has already landed, and only on its money word (rule 4).
- The board's own Motion script, its loops and its timers are dropped (`units.read_board`); CSS animations and
  transitions are switched off in the scene (`kit.js`).

## 8. No music, no sound effects

- board-sync makes picture only. The board clips and the board track have no audio stream; the preview carries the presenter's
  voice (the final-cut WAV) and nothing else. The timeline gets the WAV once, at 0 dB, with no effects.

## 9. Copy that contradicts speech is flagged, never changed

- A money number on the board that no spoken number in the board's window matches (shorthand like "three" for
  $3,000 counts as a match), and every flag written in the brief, goes into the cue file's `flags` and the QA
  report (`Board._flags`). Recalled numbers and numbers listed in the structure step are context that returns, not
  something the presenter claims on this board, so they are never checked against the presenter's words. board-sync never edits board text and never edits the presenter's words. The fix is in Claude Design.

## 10. Never drop off-script lines; ad-libs stay

- Every spoken word stays in the window it falls in, including ad-libs (windows.py); anchors are searched in all of
  the board's words, so an ad-lib can carry an element or a note.
- Spoken stretches over 15 s with no script line are reported as "propose a new board" with the spoken words
  (`cues.proposals`), never cut and never covered silently.

## Reading order

- Rows land top to bottom in spoken order. If the presenter names a lower row first, the order of the rows is kept and each
  row still lands on its own word.
