# Layout: canvas, zones, patterns

## The frame (F01)
- One board is **1920 × 1080**, white paper with a dot grid: `radial-gradient(#E5E7EB 1.5px, transparent 1.5px)` on a **40 px** tile (`background-size: 40px 40px`).
- Root element `.ebs`: `position:relative; width:1920px; height:1080px; overflow:hidden; box-sizing:border-box`, font Inter 700, colour ink. Every placed element is absolute, in board pixels (class `.n` for a placed wrapper).
- **60 px margin** on every side; nothing readable outside it.
- The paper never changes colour; full-bleed black only happens inside a burned-in insert.

## Zones (F01, Q34)
| Zone | Position |
|---|---|
| Title zone | x60 y64 · 1800×112. Titles always start at x60, y64 |
| Kicker (eyebrow over the title) | x60 y22, Mono 22 caps |
| Content | full 1800 px width above y586; left 1180 px below it (x60 to x1240) |
| Camera box | x1400 y704 · 480×336, border 1.5 px light border, radius 7, background `#151515`, shadow `--sh-film`, z 30, video `object-fit:cover` |
| Camera keep-out | x ≥ 1241, y ≥ 586 (QA box: x1241–1904 × y586–1064) |
| Credit line | x60 y1040 · 1320×30, Inter 18/30, `#9CA3AF`, .01em, one line with ellipsis |
| Handwritten note | bottom-left near x80 y914–940, or next to what it labels |
| Tag row (AR boards) | x60 y1000, left of the camera |
| QA bounds | every readable element inside x60–1860, y60–1020 (arrows exempt) |

The camera is on every board except during a full-screen insert: it fades out .25 s before, back in .35 s after (E24: comes back .05 s after the clip ends). Content never enters the keep-out rectangle.

### The L-shaped layout
Above y586 you may use the full 1800 px width. Below y586 stay left of x1241. Keep trees shallow and wide so the camera zone stays empty (D52).

## Six layout patterns (F05: "Six layouts carry most boards")
1. **Two-up hook**: Original and AI side by side, tall tiles, 40 px gap, problem cards stacked right.
2. **Stage grid**: six 280 px tiles in a row (304 px pitch), four below. Caption above every tile.
3. **Inputs → engine → result**: two inputs, curved 10 px arrows into the ink-blue engine card, result tile right.
4. **Before → after + claims**: two big squares joined by an arrow, two solid claim cards on the right.
5. **Flow chart**: 3 × 3 cards, 10 px arrows that turn corners, the last row in ink blue.
6. **Drawn row**: three flat illustrations, one stamp each, one glow on the one that matters.

## Layout rules from other boards
- **Fit the footage, not the box** (C08): box = clip width/height + the 4 px border. Change the layout to fit the footage.
- **Recurring anchor** (P66): a visual that keeps coming back (a ladder, a map, a stack) sits at exactly the same position and scale every time it returns. The zone being talked about is lit; the others drop to **14 % opacity**. Introduce it once on a map board, then return to it at each chapter. On the AR ladder boards the three blocks sit at tops 200 / 414 / 462 / 646, left 60, width 1150; dimmed blocks use opacity .16.
- **Agenda** (H143) and the **three-part anchor** (Y178) are recurring anchors too: same position every time.
- **Veil pop-up panel** (E23): x40 y186 · 1270×834, left of the camera.
- **Burned-in insert on black** (E25): the clip at its own aspect, centred (1440×1080 at x240). Wide strip variant: 1920×584.
- **Fill the board** (AR boards, implied): small content groups are scaled up as one block (scale 1.0–1.46, origin x60 y196 under the title) so the board does not look empty. Title, kicker, tag row and camera stay unscaled.
- **Lower third** (D56): bottom-left, clear of the camera and the credit line.
- **Mid-roll plug** (H146): bottom-left, clear of the camera.
- **Type collage** (P231): keep the camera zone clear on a talking-head board.

## End screen (X40, X41)
- The last 5–20 s are the end screen. The end board starts on the sign-off line and holds **≥ 20 s** so YouTube's elements can sit on it. Everything on it is on screen within 1.5 s; nothing new arrives in the last 5 s.
- **Left 900 px (x60–960)**: the claim title ("Your sign-off"), the sign-off in display size ("Your channel", 128 px, marker sweep), the real community card (r18, 8 px soft shadow) with up to three stickers, and the Instrument Serif note ("This is you").
- **Watch next**: 16:9 slot top-right, x1180 y120, 680×383. Empty paper in the export.
- **Subscribe**: ⌀210 circle at x1000 y760, left of the camera, never inside the keep-out.
- The dashed slots are guides only; they are not rendered in the export.
- Camera stays in its usual place; you looks at the viewer for the sign-off.
- No credit line on the end board unless film footage is on it.
- The end board labels the slots "RECOMMENDED VIDEO" and "SUBSCRIBE" with the community card ("Join the community", free community, your-community.link, "link in the description", FREE sticker).

## Vertical 9:16 (V153–V157)
- Boards **1080 × 1920** for Shorts / Reels, built from the same components with bigger type and the face kept clear.
- Title top (Inter 84, may wrap to 2 lines), **one visual in the middle** at full width, the camera in the **bottom 480 px** (keep it clear).
- Text ≥ 36 px.
- Footage keeps its aspect: stack 16:9 clips vertically instead of cropping.
- Same colours, stickers and motion.
- [NEEDS] side margins, exact camera box size and title position for 9:16 are not stated.

## Thumbnails (T158–T160)
- **1280 × 720**. Face + one big word or number + one visual. Max 3 words.
- Same paper, ink, soft blue marker and stickers as the video so it reads as the channel.
- Face from a real frame, never generated.
- Check it at 160 px wide before shipping.
- Three formats: big word, before / after, tool vs tool.
- [NEEDS] sizes and positions inside the thumbnail are not stated. The `youtube-thumbnails` skill owns thumbnail strategy.
