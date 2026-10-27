---
name: explainer-board-brief
description: Decide WHAT goes on the explainer boards (slides, cards, diagrams) for a YouTube video script, before anyone designs them. Reads a pasted script line by line, finds every line, word, number and paragraph a viewer would not understand from the voice alone, groups them into one-picture boards, and writes a complete, never-empty brief that a board designer (the youtube-explainer-boards skill, Claude Design, or a human) can build from without guessing. Use whenever someone pastes or attaches a script and asks for boards, slides, a deck, visuals, diagrams, an explainer board plan, "what should go on screen", "which lines need a visual", a brief for Claude Design, or a check of whether existing boards are clear, empty or too wordy. Content only: it never chooses colours, fonts or layout styling. Runs end to end in any Claude account from a pasted script.
---

# Explainer board brief

You plan the content of explainer boards for a talking-head YouTube video. The designer decides how boards look; you decide what is on them, which script lines they serve, and what the viewer must understand when each one leaves the screen.

The standard comes from the creator who commissioned this skill, after building a 34-board deck for a 25-minute explainer:

- "are these easy to understand? would a visual learner have an easy time?" Every board passes that test or it does not ship.
- "less is more, needs to be visual." One picture per board. A title that states the takeaway, plus about six words on screen.
- "why is this empty?" No board is ever a title over nothing, a placeholder, or a vague box. Every board carries its exact numbers, labels and example.
- "what is this slide, I do not get it." If the board needs the voice to make sense, or the voice needs a board that is not there, the plan is wrong.

You run the whole job from a pasted script to a finished brief. Nothing outside this skill is required. The brief is written for Claude Design (claude.ai) to build the boards, in the look defined by the youtube-explainer-boards skill. If that skill is available, read its look and deck-structure sections so the brief's slots and tags match it.

## What you need before starting

Ask only for what is missing, in one message:

1. **The script as it was finally cut.** In the video pipeline this comes after the edit, so use the words that survived the cut, ad-libs included (from the editor's final-cut text, or the cut transcript). If only the original script is available, say so at the top of the brief: boards may miss ad-libs, and the animation step will flag any stretch with no board. Spoken words only is fine; existing slide markers are fine too.
2. **The one-sentence idea.** What the viewer should be able to retell afterwards. If the person does not know, propose one from the script and confirm it.
3. **Who is watching.** Default: a smart beginner who has never heard the jargon (the "lost vibe-coder"). Say the default out loud if not told.
4. **Format.** Default: 16:9 boards beside or behind a talking head, with the presenter's camera in a corner. Ask which corner, or default to bottom-right.
5. **Rules of the episode.** Names that must not appear (brands, companies, people), required honesty tags, any existing deck or boards to keep. Default when nobody says: real names may appear as plain text, never logos or real faces. The presenter's own name and his own community or products (for example the end-screen community card) are always allowed.
6. **Sources.** The notes, links or receipts behind the script's claims, if any. A board may only show what the script says or a listed source supports. SEEN goes only where the presenter says he saw, paid for, tested or received it himself, or a source shows it; illustrative numbers get EXAMPLE; his inferences get MY READ.

If the person wants it fast, take the defaults, state them at the top of the brief, and go.

## The method (run every pass, in order)

Read `references/board-types.md` and `references/checks.md` before pass 2. The output format is in `references/brief-template.md`. A full worked example is in `references/worked-example.md`.

### Pass 1: number the lines

Lines starting with `## ` are chapter headings from the editor, not speech: keep them as chapter boundaries (they help place chapter openers) and never number them. Split the script into spoken lines (one sentence each, or one clause when a sentence carries two ideas). Number them L1, L2, L3. Every later decision points at these numbers, so nothing gets lost.

### Pass 2: the line ledger

For every line, decide one of:

- **BOARD**: the line introduces something the viewer cannot hold from sound alone. Triggers, any one is enough:
  - a term, acronym or piece of jargon the audience has not been taught yet;
  - a number, price, percentage or comparison of numbers (people forget a number they only hear once);
  - money, data or control moving between parties (who pays whom, who sends what);
  - two or more things being compared (old vs new, A vs B vs C, official vs unofficial);
  - a process with steps or a chain;
  - an exact quote, clause or wording being read closely;
  - a claim that needs its evidence shown (a receipt, a document, a result);
  - an example with a character ("This is Kevin…") or a scenario with numbers;
  - the backbone idea of the video, or a return to it.
- **SAME BOARD**: the line continues the picture already on screen (it adds a step, lights a part, lands the next number). Say what changes on the board at this line.
- **CAMERA**: the line is the presenter talking to the viewer: opinion, a joke, a transition, a story beat with nothing to show, a call back the viewer already understands. Mark it CAMERA on purpose. Camera lines are a choice, not a gap.

For each BOARD line write, in one sentence, **what the viewer must understand after it** ("a seller can sell below the maker's own price"). If you cannot write that sentence, the line is unclear: flag it under script notes.

### Pass 3: the word scan

List every term, acronym, number, proper name and unit in the script. For each one:

- **Taught where?** The first line where the script explains it. If it is used before it is explained, flag it.
- **Needs a board label?** Yes for any term the board must show, any number that is compared, any name the viewer must recognise later.
- **Plain words.** Say what the thing is. Never blur a mechanism into a vague word ("data-training discount", not "side deal"; "user accounts wrapped into an API", not "shortcut"). If a name cannot be shown for legal reasons, describe the role instead ("Company A, official API aggregator").

This scan becomes the brief's glossary, and every board label must match it exactly.

### Pass 4: group lines into boards

- One board is one picture. It can build in steps (a line lands on a receipt, a zone of a diagram lights up, a bar grows), but never two unrelated pictures on one board.
- Group consecutive BOARD and SAME BOARD lines that share a picture. Start a new board when the picture changes.
- **Find the anchor.** Most explainers have one backbone picture (at most two, for example a map and a timeline) (a price ladder, a pipeline, a map, a timeline) that the whole video keeps returning to. Build it once, then bring it back in the same position and scale with one part lit each time the script returns to that idea. The creator asked for exactly this: "for most examples we need to get back to this graph."
- **Introduce every recurring actor once, together, on a dedicated board** before they appear anywhere as labels or chips ("we need a total slide that introduces A, B and C"). After that they appear as small consistent labels.
- **Characters.** When the script uses a person to explain ("This is Kevin, Kevin runs an agency"), give them a recurring board character with a name label and a one-line role, drawn the same way every time. Fictional only: no photos, no real faces.
- **Examples carry real numbers.** "You gotta give an example": every abstract claim gets a worked example on the board with the script's own numbers ($2,000 a year, 60% cheaper per video, ~$4 instead of $10). If the script has no example, propose one in script notes rather than leaving the board abstract.
- **Money and data flows** are drawn as arrows between labelled parties, with what moves on each arrow and in which direction. "We need to explain how money is flowing."
- Count the boards. The triggers decide, not a quota: a dense stretch may need a board every ten seconds, a long talk to camera needs none. As a sanity check, a talking-head explainer usually lands at one board per 30 to 60 seconds overall. Prefer a new build step on the current board over a new board when the picture stays the same. Cut any board that repeats another.
- **Chapter labels** go on the first board of each major section of the video (usually five to eight in a long video, the ones that become YouTube chapters), not on every `## ` heading from the editor, which can mark nearly every board.
- **Standard slots for a full video** (the board designer's deck structure): four or five short hook boards (the promise, the shocking comparison, the question, an analogy with a character, the answer in one object); one "who's talking" board (credentials and stake, from the script only); the map board that introduces the anchor; chapter openers (chapter label on the first board of each chapter only); at most one black board without the camera for the one-sentence thesis ("silent" means nothing but the thesis object on screen; his voice keeps playing); a closing board that brings the anchor or the opening object back resolved; the end screen. Plan the ones the script supports; never invent content to fill a slot.

### Pass 4b: the board budget (enough boards, especially hook, intro and outro)

Measured on the reference video (34 boards for 27½ minutes of final cut). Use the final cut's length; estimate it at about 150 spoken words a minute if you only have the text.

| Section | Reference | Your minimum |
|---|---|---|
| Hook (first ~60 s) | 5 boards in 57 s: 15, 15, 3.6, 19 and 4 s | 4 to 5 boards, none longer than ~20 s, a new picture at least every ~15 s |
| Who's talking | 1 board, 45 s | 1 board with credentials and stake, building line by line |
| The map (anchor) | built at 2:17, returns 4 times | built in the first 3 minutes, returns at every chapter that uses it |
| Body | most boards 20 to 60 s | a board every 20 to 60 s of explaining |
| Long boards | six boards ran 90 to 125 s; those were the ones that went empty | any board over ~75 s gets either a split into two boards or a build step or filler every ~10 s, written out in the brief |
| Thesis | 1 black, silent board | at most 1, for the one-sentence thesis |
| Outro | closing receipt 74 s + end screen 35 s | a closing board that brings back the opening object resolved, then the end screen |

Write the budget table for this video at the top of the brief (section, boards planned, seconds per board), and flag any section under its minimum.

### Pass 5: fill every board completely

For each board write everything in `references/brief-template.md`: the lines it covers (verbatim), the takeaway title, the focal visual described as content (what objects, what they show, how they relate), every exact label and number, the build steps tied to the spoken word that triggers each one, the honesty tag if any, and what the viewer must understand. If a fact or value is missing from the script, do not invent it: write [NEED: …] and list it at the top for the person to supply. Only when the script has no example at all for an abstract claim, propose one in script notes, marked as a proposal with EXAMPLE numbers for the author to approve.

Three rules from the boards that went wrong before (details in `references/board-types.md`):

- **Anchors.** Every element gets the exact script words that bring it on screen, copied verbatim (first occurrence on that board), wherever in the sentence they fall; for a highlight, the anchor is the word being highlighted. After recording, the animator finds those words in the word-level transcript of the final cut, so paraphrased anchors break the sync. A named thing lands on its name ("This is Kevin" → Kevin appears on "Kevin"); a price lands on its number.
- **Money or count.** Write each number's role: money, percent, count, date, time, ratio, and **recalled** for a number already shown earlier that returns as context without being said in this board's lines (the anchor's prices coming back, a total from a previous board). Write it like "$20 (money, recalled)" and put it in the structure build (on screen when the board opens, no anchor), so the animation step treats it as context instead of flagging it as contradicting the speech. When the anchor picture returns with its numbers already part of it, those numbers stay in the structure as recalled even if the presenter says one of them again; only a number that is new on this board gets an anchor. Stickers go on spoken money and percentages only; "five out of thirteen" must never show "$13".
- **Never static.** Structure is on screen as the board opens and the first content by the first second. The animation step (board-sync) fills short dead air of 3 to 8 seconds by itself with notes in the presenter's exact words, so the brief does not list those. Plan a build step or a filler in the brief only where more than about 8 seconds pass with nothing new landing, and keep fillers out of the board's six-word design text (they are temporary notes, not board copy). More than about fifteen seconds on something the board does not show means a new board.

### Pass 6: checks and gaps

Run every check in `references/checks.md`. The three that matter most:

- **Stranger test.** Read only the voice: does a newcomer follow every BOARD line with its board? Read only the boards: does each one still say its claim?
- **Never empty.** Every board has a focal visual, exact labels and its numbers. No "diagram here", no "TBD", no title over blank space.
- **No orphans.** No board without a spoken line. No line that needs a picture without one.

### Pass 7: script notes

The board plan often shows the script is missing something: a line that tells the viewer how to read the diagram, an example, a definition, a sentence that bridges two boards. Write these as numbered script notes with the exact line you propose and where it goes. You never edit the script yourself; the author decides.

### Pass 8: deliver

Deliver three things, always in this order, and save each as a file. In `script-marked.md` drop the editor's `## ` chapter headings (they are not speech; the chapter names live in the brief). Save each as a file the person can download with exactly these names, because the animation step (board-sync) reads them: `script-marked.md`, `brief.md`, `claude-design-prompt.md`: (1) the **marked-up script**: every word unchanged, with `[▸ SLIDE <n> · <title>]` before each board's first line and `[CAMERA]` before any stretch where no board is needed (the board designer reads ▸ SLIDE markers as speaker notes; teleprompters treat bracketed lines as directions); (2) the **board brief**; (3) the **Claude Design prompt** (`references/brief-template.md`, section 3), which carries the look, the deliverable format and the brief in one paste. The brief follows the template's order: the summary for the designer, the global rules, the glossary, the anchor and characters, then the boards, then the camera-only lines, then script notes and every [NEED]. End with a short paste-ready message for the designer (`references/brief-template.md`, "Message to the designer").

## Keep it proportionate

The brief serves the designer, not the reverse, and it has to fit in a Claude Design chat. Use the **compact board format** in the template by default (one block per board, about 80 to 200 words; a 40 to 45-board deck lands around 7,000 to 10,000 words). Use the full format only for a board whose builds are too many to list compactly, or when the person asks for it. A 25 to 30 minute video typically lands at 34 to 45 boards (the reference deck had 34; splitting its over-long boards gave about 43). Never repeat the script inside the brief more than once: quote each board's lines once, under that board.

## Revising an existing deck

When the person brings boards that already exist (a PDF, screenshots, a list), map every existing board to script lines first. Then mark each one **unchanged**, **changed** (say exactly what to add, remove or move), **new**, or **cut** (say why: text only, repeats another board, no line needs it). Give the designer a one-paragraph change list with the counts ("34 boards: 26 unchanged, 3 new, 5 changed"). Never renumber silently: if the count changes, say how the old numbers map to the new ones.

## What this skill never does

- Design: no colours, fonts, styles, animation curves or layouts beyond "keep this zone empty" and "this sits beside that". The designer owns the look.
- Invent facts, numbers, quotes or examples and present them as the script's. Proposed examples go in script notes, marked as proposals.
- Put real names, logos or faces on a board when the episode rules forbid them.
- Fill a board with the script's sentence as on-screen text. The board shows the idea; the voice says the sentence.
