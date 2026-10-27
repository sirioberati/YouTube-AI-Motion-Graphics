# Board catalog

The 74 starter boards in this repo, by group. Each line: file · what it is · what it is for · **say it when** (the words you would actually say in a video, so a sync agent can find the right board from your transcript). Open any board in `boards/` to see it live.

## Diagrams

- `D43Bars.html` · **Bar chart** · Bars: 110 px wide, 4 px ink border (no bottom), r10 top, blue; the one the voice is about is mint + 8 px accent ring. · say it when: comparing amounts, 'this one is way bigger'
- `D44Line.html` · **Line chart** · Line: 10 px blue, round joins, draws on with stroke-dashoffset over ~3 s (power2.inOut) while the voice tells the story left to right; a accent 30 px dot rides the head of the line (offset-path). · say it when: 'it went up', 'over time', growth
- `D45Numbers.html` · **Share and big numbers** · Donut: 64 px ring, track #EFF6FF, value blue, 4 px ink outlines; it fills clockwise from 12 o'clock (1.6 s power3.out) while the centre number counts up with it. · say it when: 'X percent', one big number, a share
- `D46Pyramid.html` · **Pyramid** · For anything that builds up (foundations → result, needs → goals). · say it when: 'it all builds on', foundations
- `D47Cycle.html` · **Cycle / loop** · For any repeating process (iterate, feedback loop, flywheel). · say it when: 'loop', 'repeat', 'over and over', feedback
- `D48Funnel.html` · **Funnel** · For anything that narrows: attempts → results, visitors → buyers. · say it when: 'out of all of these, only', narrowing down
- `D49Timeline.html` · **Timeline** · For history and sequence. · say it when: 'first… then… in 2024', history
- `D50Venn.html` · **Venn** · For overlap: two (or three) circles slide in from the sides (x ∓160 → 0, .6 s power3.out), 8 px strokes, 14–18 % fills of their colour. · say it when: 'where these overlap', 'both'
- `D51Matrix.html` · **2×2 matrix** · For trade-offs. · say it when: 'trade-off', 'fast but expensive'
- `D52Tree.html` · **Tree** · For breakdowns (what something is made of, a decision tree). · say it when: 'it's made of', 'breaks down into'
- `D53Steps.html` · **Numbered steps** · For how-to sequences. · say it when: 'step one, step two', how-to
- `D54Terminal.html` · **Terminal** · For commands and code. · say it when: 'run this command', 'type this'
- `D56Chapter.html` · **Chapter divider + lower third** · Chapter divider (a 2–3 s beat between big parts): chapter number in Mono 220 blue rising in, the chapter name at 104 px with the marker sweep, "chapter n of m · timestamp" in Mono, progress pips (done = blue). · say it when: 'part two', 'now let's move on to'
- `D57Quote.html` · **Kinetic quote** · For the one line people should remember. · say it when: the one line people should remember
- `Y165Devices.html` · **Device connections** · For "what is connected to what". · say it when: 'connected to', 'talks to'

## Charts

- `C108Waterfall.html` · **Waterfall** · For anything built up or broken down: price, cost, time. · say it when: 'it adds up to', 'where the cost goes'
- `C109Stacked.html` · **Stacked bars** · For totals made of parts. · say it when: 'the total is made of'
- `C110Grouped.html` · **Grouped bars** · For several things compared on several criteria. · say it when: 'compared on price, speed and quality'
- `C111Slope.html` · **Slope chart** · For change between two moments (before / after a fix, last year / now). · say it when: 'before and after', 'it went from X to Y'
- `C112Scatter.html` · **Dot plot** · For two qualities at once (cost vs quality, speed vs control). · say it when: 'cheap but slow', two qualities at once
- `C113KPI.html` · **KPI row + sparklines** · For the numbers that matter (repo stars, members, cost, views). · say it when: 'the numbers', stars, views, members
- `C114Ranking.html` · **Ranking table** · For a verdict across many tools. · say it when: 'the best one is', ranking tools
- `C115Gauge.html` · **Gauge + progress** · Gauge for a judgement on a scale (realism, risk): three zones (coral / accent / mint), the needle swings in with overshoot (back.out) while the number counts up. · say it when: 'how risky', 'how real', a score on a scale
- `C116Heatmap.html` · **Heatmap** · For activity over time (generations per day, commits, uploads). · say it when: 'every day', activity over time
- `Y163Share.html` · **Share split** · For any "how much is X, how much is Y" split. · say it when: 'how much is X, how much is Y'

## Component motion

- `C239PriceCard.html` · **Price card reveal** · The card itself masks up from its bottom edge; then its contents stagger in top to bottom (label, price, line, chips); last, a sticker pops on the corner. · say it when: 'it costs', a price
- `C240TableFocus.html` · **Table: cascade + row focus** · The table wipes down, rows slide in one by one; when the voice names the answer, that row turns accent and lifts while every other row dims. · say it when: 'and the answer is this row'
- `C241ChartFocus.html` · **Chart: build + focus bar** · The axis draws, bars grow from the baseline with a stagger; on the key word every other bar goes grey and dims, the hero bar lifts, and a callout pops with a drawn leader line. · say it when: 'look at this bar'
- `C242AppFocus.html` · **App window: build + focus area** · The window outline draws, the app wipes down inside it; on the key word the rest of the app dims, a accent frame snaps onto the area that matters and a label rises under it. · say it when: 'in the app, click here', a UI area
- `C243CodeFocus.html` · **Code panel: type + line focus** · The panel slides in, each line types on left to right in order; when the voice explains one line, a accent band sweeps across it with a thick left marker. · say it when: 'this line does', explaining code
- `C244Receipt.html` · **Receipt prints out** · The receipt feeds out of a printer slot in small steps (like a real printer), line items first, total last; then a stamp slams on it. · say it when: 'the bill', 'what you pay'
- `C245NodeGraph.html` · **Node graph: build + pulse + focus** · Nodes pop left to right, edges draw between them, then data pulses along every edge (accent dots); last, the node being talked about gets an blue halo while the rest dim. · say it when: 'the data flows through', a pipeline
- `C246Phone.html` · **Phone: spring + scroll + notify** · The phone springs up from below with a little tilt that settles; the feed inside scrolls smoothly; then a notification drops from the top with a bounce. · say it when: 'on your phone', a notification
- `C247ChipFilter.html` · **Chips: cloud → filter** · Chips pop in as a cloud; on the key word the ones not chosen shrink and fade, and the chosen accent chips travel into one clean row under a label. · say it when: 'out of all these options, pick'
- `C248KPIFocus.html` · **KPI tiles: flip + count + focus** · Tiles flip down from their top edge one after another; each number counts up while its sparkline draws; then the tile that matters lifts with a soft colour halo and the other three dim. · say it when: 'the number that matters'
- `C249VersusCards.html` · **Versus cards: enter + winner** · Cards slide in from opposite sides, the "vs" disc spins in between; on the verdict the winner lifts and tilts with a accent glow and a sticker, while the loser shrinks, greys and dims. · say it when: 'X vs Y, and the winner is'
- `C251FolderTree.html` · **Folder tree: grow + open** · The root pops, the trunk grows down and each branch draws out with its folder sliding in; on the key word one folder gets an blue ring, the rest dim, and a preview of what's inside wipes open beside it. · say it when: 'open this folder'
- `C252Lens.html` · **Magnifier lens** · For finding one value in a lot of data. · say it when: 'look closer', finding one value
- `C254DealPull.html` · **Stack: deal + pull one out** · Cards are dealt onto a pile from off-board with a spin, each slightly offset; on the key word the chosen card is pulled out of the middle and comes to the front with a spring, while the pile darkens a little. · say it when: 'pick one out of the pile'

## Premium motion

- `P36Focus.html` · **Focus pull** · When the voice walks through a list, one thing is in focus at a time: the named card and its footage come to full opacity, scale 1.03 and get the 7 px marker glow; everything else on the board drops to opacity .32 (the player's contextUntil / steps). · say it when: walking through a list, 'first this, then this' (focus pull)
- `P37Keyframes.html` · **Keyframes** · When something exists before and after a moment, it travels: one node keeps its identity and tweens between keyframes (x, y, scale, origin 0 0). · say it when: 'it moves from here to there' (keyframes)
- `P196Kinetic.html` · **Kinetic type** · For a punchline with numbers. · say it when: a punchline with numbers
- `P197MaskReveal.html` · **Mask line reveal** · For a statement title. · say it when: a statement title
- `P198Odometer.html` · **Odometer roll** · For a payoff number. · say it when: the payoff number
- `P199Scramble.html` · **Scramble decode** · For a code-ish name appearing (a skill, a file, a command). · say it when: a name appearing: a skill, a file, a command
- `P200LineDraw.html` · **Line draw + follow** · For "from here to there". · say it when: 'from here to there' (line draw)
- `P209Flip.html` · **Card flip** · For before / after on one card, or question → answer. · say it when: 'before / after', question to answer
- `P211Fan.html` · **Deck fan-out** · For "there are N of these" (options, versions, takes). · say it when: 'there are N of these', options, versions
- `P217Cable.html` · **Live cable** · For two things that stay connected while they move. · say it when: 'connected', stays linked while moving
- `P218Loader.html` · **Loader → done** · For "it runs, then it's finished". · say it when: 'it runs… and it's done'
- `P219Chat.html` · **Chat + typing** · For talking to an agent or a person on screen. · say it when: 'I asked it', talking to an agent
- `P220LetterWave.html` · **Letter wave** · For one emphasised word held on screen. · say it when: one emphasised word
- `P221Confetti.html` · **Confetti burst** · For a win moment (published, done, milestone). · say it when: 'it worked', 'done', a win
- `P226LiquidFill.html` · **Liquid text fill** · For "filling up" (progress, capacity, a goal reached). · say it when: 'filling up', progress, capacity
- `P227ScribbleFill.html` · **Scribble fill** · For a chart or shape that gets "coloured in". · say it when: 'colour it in' (scribble fill)
- `P228CrossOut.html` · **Cross out + rewrite** · For "not this, that" (old way → new way, wrong → right). · say it when: 'not this, that', old way to new way
- `P230WordSlot.html` · **Rotating word** · For "it does X, Y and Z" in a title. · say it when: 'it does X, Y and Z'
- `P236Checklist.html` · **Scribble checklist** · For progress through a list. · say it when: 'done, done, next' (checklist)
- `P237Highlighter.html` · **Highlighter sweep** · For a quote or paragraph where two phrases carry the point. · say it when: the two phrases that matter (scribble highlight)

## Workflows and code

- `W69Nodes.html` · **Node graph** · For a pipeline shown as a system: white nodes (4 px ink, r16, soft shadow), tinted header, a real thumbnail at true aspect, one Mono line of output. · say it when: 'the workflow', a pipeline as a system
- `Y175Render.html` · **Render pipeline** · For "how code becomes a video". · say it when: 'how code becomes a video'
- `Y182SystemMap.html` · **Steps on a track** · For a whole process in N steps. · say it when: 'the whole process in N steps'
- `A136FileAnatomy.html` · **File anatomy** · For config files, skills, prompts as files. · say it when: 'the skill file', 'the prompt file'
- `A137FolderTree.html` · **Folder tree** · For "where do I find it". · say it when: 'where do I find it'
- `A138Diff.html` · **Diff view** · For "change this to that". · say it when: 'change this to that'
- `A139ErrorFix.html` · **Error → fix** · For debugging moments. · say it when: 'it broke, here's the fix'
- `A141Decision.html` · **Decision flowchart** · For "which one do I pick". · say it when: 'which one do I pick'
- `B134Request.html` · **Request → response** · For "what is an API". · say it when: 'what is an API', request and response

## Story and comparisons

- `H143Agenda.html` · **Agenda / chapter map** · Shown once early, then returns between chapters: done chapters fade to 45 % with ✓, the current one is accent with the ring, the rest wait. · say it when: 'here's what we'll cover', chapters
- `H144MythFact.html` · **Myth vs fact** · For correcting a belief. · say it when: correcting a belief, 'everyone thinks… but'
- `H145Recap.html` · **3 things to remember** · Before the end screen: three cards, number in Mono 64, the lesson in Inter 40, dealt one per spoken point. · say it when: 'three things to remember'
- `Y164Versus.html` · **Versus ledger** · For two options compared on several measures. · say it when: 'X vs Y on several things'
- `K123Scorecard.html` · **Scorecard** · For "which one should I use". · say it when: 'which one should I use'
- `X41EndLayout.html` · **End-screen layout** · Timing: the end board starts on the sign-off line and holds ≥ 20 s so YouTube's elements can sit on it. · say it when: the sign-off, end screen

## Two boards, same job

- `C113KPI` and `C248KPIFocus` both show key numbers. Keep `C248KPIFocus` when one number is the point; `C113KPI` when they all matter.
- `C245NodeGraph` and `W69Nodes` both show a pipeline. Keep `C245NodeGraph` for data flowing; `W69Nodes` when each step has an output to show.
- `C251FolderTree` and `A137FolderTree` both show folders. Keep `C251FolderTree` when one folder gets opened; `A137FolderTree` for the whole map.
- `Y164Versus`, `C249VersusCards` and `K123Scorecard` all compare. Two options with a winner: `C249VersusCards`. Two on many measures: `Y164Versus`. Three or more: `K123Scorecard`.
