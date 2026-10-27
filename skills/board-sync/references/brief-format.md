# What board-sync reads from script-marked.md and brief.md

Both files come from step 3 (the explainer-board-brief skill). board-sync only reads them; it never rewrites them.
Paths are given on the command line (`--script`, `--brief`); in the trainee layout they are
`03-board-brief\script-marked.md` and `03-board-brief\brief.md`.

## script-marked.md (read by windows.py)

The full script, every word unchanged, with marker lines:

```
[▸ SLIDE 4 · Your own team, cheaper]
Think about it like this. This is Kevin.
[CAMERA]
So that's exactly what is happening with AI APIs right now.
```

| What | How it is read | If it is missing or off |
|---|---|---|
| `[▸ SLIDE <n> · <title>]` | Starts board n's block. Also accepted: `►`, `>`, `-` or `:` instead of `·`, no title. | No markers at all: the windows stage stops and says so. |
| `[CAMERA]` | Starts a camera-only stretch (the board track is black there). | Lines stay with the board before. |
| `## …` headings (chapters such as `## Ch 4 · …`) | Ignored: only the bracketed markers count. | Nothing changes. |
| The lines under a marker | Aligned to the spoken words in order; the block's first matched word sets the board's start (0.15 s before it), the next block's start sets its end. `L12` line numbers and inline `[directions]` are ignored. | A block matched under 40 % is reported, not guessed; a block with no lines (a hold board) takes the gap between its neighbours. |
| Words said that are not in the script | Kept in whichever window they fall in (ad-libs are never dropped). | A stretch over 15 s with no script line is proposed as a new board. |

The board number n is matched to the board file by its leading number: `04-OwnTeam.html` is board 4.

## brief.md (read by brief.py → brief.json)

board-sync reads only the **Boards** section: every heading `### Board <n> · <title>` and the fields under it. Both
board formats are accepted, and they can be mixed. Headings may vary in punctuation (`## Board 4: …`, `### Slide 4 -
…`), boards may be in any order, and a later duplicate replaces an earlier one (with a warning). The other sections
(glossary, anchor, characters, camera-only lines, script notes, checks, transcription fixes) are for people and are
ignored.

### Compact format (the default)

```
### Board 17 · Above the list, and under it  (L180–L190, bar chart)
Title: "Above the list, and under it" (highlight "under it")
Understand: the same clip sells above the model maker's list and under it.
Visual: three bars on a $10 list line …
Builds: structure: the baseline, the dashed list line, "$10" (money, recalled) · "B app + API" → "Company B, the app" · "$14" (money) → "30 percent of 20 is 14" · $500,000 (money) → "half a million dollars"
Fillers: "B still makes profit" → "still makes profit" · "$7.50" (sticker) → "750"
Tag / flags: SIMPLIFIED · MY READ on C · copy "$500,000 a year" vs spoken "every single day"
```

The newer compact blocks have a `Title:` line and no `On screen` line: every exact label and number is listed once
inside `Builds`, with its role in brackets right after it (`"$20" (money, recalled)`, `$500,000 (money) → "…"`, or
inside the quotes: `"List price · $10 (money, recalled)"`). Older compact blocks with an `On screen` line and the full
format still parse; when both name a number, one entry is kept per number and role (a recalled role wins).

### Full format

```
### Board 4 · Your own team, cheaper
- **Window:** 0:34–0:53 (19.1 s)
- **Lines:** L6–L11
  > L6 Think about it like this.
- **The viewer must understand:** …
- **Type:** Character scene + number sticker
- **Focal visual:** …
- **On screen, exactly:** title "Your own team, cheaper" · price card "$5,000" (money) · title keyword to highlight: "cheaper"
- **Builds (element → anchor words):**
  1. structure as the board opens: title, empty stage
  2. Kevin + name + role line → "This is Kevin."
  3. price card "$5,000" → "$5,000"
- **Fillers:** none needed; something lands every few seconds.
- **Tag:** none (an analogy)
- **Returns to the anchor:** no
- **Flags:** "three" is money: print "$3,000".
```

### The fields and what they do

| Field | Becomes | Used for | If missing |
|---|---|---|---|
| heading `Board <n> · <title>` | `n`, `title` (and `lines`, `type` from a compact heading's parentheses) | matching the board file `NN-…html` | a board with no entry: every element anchored by its own text, and the report says so |
| `Lines` (+ quoted `>` lines) | `lines` ("L6–L11"), `quoted` | the manifest | empty |
| `Window` | `window` | the manifest | empty |
| `Type`, `Understand`, `Visual` | `type`, `understand`, `visual` | `silent` = the brief calls it the black silent board (camera-zone check off) | empty |
| `Title` | `title_line` (and `title` when the heading has none), `highlight` from `(highlight "…")` | the headline word that pops | the heading's title |
| `On screen` | `onscreen`, `numbers`, `highlight` | number roles (`money+recalled` and the like); the headline word that pops (`title keyword to highlight: "…"`) | no roles: `$` numbers count as money and `%` numbers as percent; the highlight is the board's own marked word |
| `Builds` | `builds` = `[{element, anchor, anchors}]` | when each element lands (see below) | every element anchored by its own text |
| `Fillers` | `fillers` = `[{text, anchor, style, near}]` | notes for long talk with nothing to land | board-sync's auto notes cover the gaps |
| `Tag` / `Tag / flags` | `tag`, `flags` | the honesty tags stay on screen from 0.25 s; flags go to the report | empty |
| `Flags` | `flags` (one per line) | copied to the cue file and the QA report, never acted on | empty |

### Builds: the element side

One build per numbered line (full format) or per ` · ` part (compact format; a `·` inside quotes does not split).
The element is found on the board in this order:

1. `#u7` (a unit id from `units/NN.json`): exactly that element. For fine-tuning after a first run.
2. Quoted text: the element whose text is that text (`"$5,000"`, `"LINE 1"`, `"prompts · images · videos"`). When
   the same text is on the board several times, each build takes the next one not yet used, in reading order.
3. Unquoted names that are an element's whole text (`Kevin + label`).
4. Kind words for textless things: figure, circle, arrow, underline, line, bar, box, card, receipt, sticker, chip,
   icon, tile, tag, baseline, rail, axis… The nearest unused element of that kind to the other elements named in
   the same build (or to the previous build's) is taken. `arrow from "6M" to the row` uses "6M" only as a reference.
5. `+` and `,` join several elements into one build; they land 0.1 s apart in the order written.

An element that cannot be found is reported ("element not found on the board"), with the build's text.

### Builds: the anchor side

| Written as | Meaning |
|---|---|
| `"verbatim words"` | lands on those words (tolerant matching; see rules.md rule 2) |
| `"a", "b", "c"` | several elements (rows) land on these phrases one by one |
| `structure` (or the line starts `structure as the board opens:`) | on screen as the board opens (0.45 s cascade) |
| `with: "Kevin"` | 0.1 s after the element with that text lands |
| `+0.15` | 0.15 s after the previous build |
| `@12.4` | at 12.4 s into the board (not tied to a word; avoid: it does not survive a re-cut) |
| `hide` | never shown (and reported) |
| nothing | the element's own text, as with no brief |

### Fillers

`"note text" (style) near <element> → "anchor words"`. Style is one of hand (default), sticker, tag, mono, stamp. With
no arrow the note's own text is the anchor (the presenter's exact words). A filler that describes a mark with no words of its own
(`underline under the empty slot → "I really want you to know this."`) is written as the spoken anchor words in the hand
style; board-sync never invents a drawing. `\n` in the note text is a line break.

### Numbers and their roles

Written next to the quoted text: `"$5,000" (money)`, `"5 of 13" (count)`, `"≈$9.40 · 6% under" (money, percent)`,
`"$20" (money, recalled)`, `"2×" (ratio)`, `"≈10 seconds" (time)`. Known roles: money, percent, count, time, date,
ratio (also written fraction), recalled. Only money and percent numbers can stamp, and only when spoken as money or
percent; time, ratio, count and date never stamp. Words in the brackets that are not roles (`(money, said 'three')`,
`(orange)`) are ignored; with no role at all the role is inferred from the text. Role notes are removed from the
element text before it is matched to the board.

**recalled** marks a number that returns as context (a ladder rung, a price from an earlier board) and is not spoken
in this board's lines. The brief also lists it in the structure step (step 1, no anchor). board-sync treats it, and
everything else listed in the structure step, as context: it is revealed with the structure cascade as the board
opens, it never stamps, and it is never checked against the presenter's words (no copy flag). A recalled number that a later
build anchors on words keeps that anchor.

### When brief.md is missing

brief.json is written with `"missing": true`. Every element is anchored by its own text (the strongest word or number
in it, searched in the presenter's words), textless parts land with what they hold or touch, structure opens the board, auto notes
fill the gaps, and the QA report says the brief was missing.
