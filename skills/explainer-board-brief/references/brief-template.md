# The brief: output format

Deliver three things in this order: the **marked-up script** (for the presenter, the editor and the designer), the **board brief** (for the designer), and the **message to the designer**. Write in plain words. The designer has never seen the script discussion, so the brief must stand alone.

## 1. Marked-up script

The full script, every word unchanged, with a marker line before each board's first line, and a camera marker where the board drops away:

```
[▸ SLIDE 4 · Your own team, cheaper]
Think about it like this. This is Kevin, and Kevin runs an agency…
[CAMERA]
That's exactly what's happening with AI APIs right now.
[▸ SLIDE 5 · The answer is on a receipt]
…
```

Use exactly `[▸ SLIDE <n> · <title>]` and `[CAMERA]`. The board designer reads each ▸ SLIDE marker and takes the lines under it as that slide's speaker notes (lines under `[CAMERA]` stay with the slide before as notes, and the editor may cut to full camera there). Teleprompters treat bracketed lines as directions, so the presenter can record from this file.

## 2. Board brief

```
# <Video title>: board brief (<N> boards)

## For the designer, in one paragraph
<What the video teaches in one sentence. How many boards. Which board is the anchor and where it returns. Which characters recur. The text limit. The camera zone. What is new/changed/cut if revising.>

## Before you start: missing values
- [NEED: …] (who supplies it, which board waits for it)

## Global rules
- Format: 16:9, presenter's camera bottom-right (keep that zone empty: no text, chips, arrows).
- Text: a takeaway title plus about six words per board; labels and numbers are extra.
- One picture per board; boards may build in steps; nothing moves again once it has landed unless the script calls for it.
- Names: <allowed / forbidden names and how to refer to them>.
- Honesty tags used in this video: <SEEN / EXAMPLE / MY READ / SIMPLIFIED>, only where listed.
- Every element lands on its anchor words, never before them.

## Glossary (use these words exactly)
| Term on the board | What it means, in plain words | First taught at |

## The anchor
<Name. What it shows in full: every part, label and value. The boards where it returns and which part is lit each time.>

## Characters and recurring actors
| Name | One-line role | First board | Appears on |

## Boards
### Board <n> · <takeaway title>   [NEW | CHANGED | UNCHANGED, when revising]
- **Lines:** L<a>–L<b>
  > the exact script lines this board covers
- **The viewer must understand:** <one sentence>
- **Type:** <from board-types.md>
- **Focal visual:** <the objects, what each shows, how they relate; content only, no styling>
- **On screen, exactly:** title "<…>" · labels "<…>", "<…>" · numbers "<$500,000 (money)>", "<5 of 13 (count)>", "<$20 (money, recalled)>"
- **Builds (element → anchor words):**
  1. structure as the board opens: <…, including every recalled number>
  2. <element> → "<verbatim words>"
  3. <element> → "<verbatim words>"
- **Fillers:** <for any stretch over ~3–4 s with nothing landing: the presenter's exact words as a note, a sticker, a tag>
- **Tag:** <SEEN / EXAMPLE / MY READ / SIMPLIFIED / none>
- **Returns to the anchor:** <yes: which part lit / no>
- **Flags:** <contradictions with the script, open questions>

## Transcription fixes (for the captions step)
Words the transcript got wrong, with the right word and the line ("tent" → "ten", L212). Never change the script for these; they are fixed in the captions and the description.

## Camera-only lines
L<x>, L<y>, … (and why, in a word: opinion, joke, transition, already on screen)

## Script notes (proposals for the author; nothing has been changed)
1. After L<n>, add: "<proposed line>". Why: <the board needs it / the viewer needs it>.

## Checks run
<The checks from checks.md with pass/fixed for each.>
```



## Compact board format (the default)

Use "→" only between an element and its anchor words. Inside a label, write the arrow as a word ("to") or draw it in the visual, so the animation step never mistakes a label for an anchor.

```
### Board <n> · <takeaway title>  (L<a>–L<b>, <type>)
Understand: <one sentence>
Visual: <objects and how they relate>
Title: "<takeaway>"
Builds (every exact label and number appears once, here): structure: <…, recalled numbers> · <element "exact words" (role)> → "<anchor words>" · …
Tag / flags: <…>
```

## 3. The Claude Design prompt (paste-ready)

One message the person pastes into Claude Design, with the marked-up script and the brief attached (and the youtube-explainer-boards SKILL.md if they have it). Fill the angle brackets:

```
Build the explainer boards for my YouTube video "<title>": <N> boards, 16:9 (1920×1080), one standalone HTML file per board.

EXAMPLE: the attached example boards (from the reference deck, for example 02, 08, 13 and 28) show the finished look and the export format. Match their style; the content comes only from the brief.

LOOK: use the attached youtube-explainer-boards SKILL.md exactly (white dotted paper, hand-drawn boxes and arrows, yellow highlighter on the title, receipts, stickers, the hand font). Do not restyle. If that file is not attached: <one line describing the look the person wants>.

WHAT GOES ON EACH BOARD: the attached board brief. Build exactly the boards it lists, in its order, with its exact words, labels and numbers. Use the glossary words exactly. Nothing on a board that the brief does not list, except the look's own furniture.

SPEAKER NOTES: the attached marked-up script. Each "[▸ SLIDE N · Title]" marker starts board N; the lines under it are that board's speaker notes. Lines under "[CAMERA]" stay with the board before.

BUILD ORDER: each board builds in the order of its "Builds" list. Structure is on screen when the board opens; every label, name and number appears only on its anchor words. Nothing moves after it lands. No zooms, no pulses, no sound.

CAMERA ZONE: the presenter's camera covers the bottom-right corner, 32% of the width × 40% of the height, 40 px in from the right and bottom edges (about 615 × 430 px). Keep it completely empty on every board except <the black silent board, if any>.

FILES: the same export format as the example deck: name each file NN-Short-Name.html (01-…, 02-…), with fonts and media in an assets folder, plus an index.html listing every board with its notes and a speaker-notes.md. These files are animated to the voice in the next step, so keep every text element as real text (not an image) and give each build group its own element.

When done, list any board where you deviated from the brief and why.
```

## 4. Short message (if the designer already has the brief)

"Here is the board brief for <video>: <N> boards, one picture each, built in the order listed. The anchor is <name>, built on board <n> and returning on <list>. Characters: <list>. Keep the bottom-right camera zone empty. Every element lands on the words listed under Builds; nothing appears before its words. Use the glossary words exactly. Missing values are marked [NEED]; leave those boards for last. Design is yours: the brief only says what goes on each board."
