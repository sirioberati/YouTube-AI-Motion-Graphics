# Tokens: colour, type, shape

The "Clean minimal" starter theme. Change these to make the boards yours: swap the values here and in `assets/brand.css`, then run your checks.

## Colour: slate ink, soft grey paper, one blue accent

### Ink and paper
| Token | Hex | Use |
|---|---|---|
| Ink | `#1F2937` | all text |
| Deep ink | `#111827` | code panels, dark chips |
| Paper | `#FFFFFF` | board ground |
| Wash | `#F6F7F9` | soft grey panels |
| Line | `#E5E7EB` | card borders (1.5 px), dividers |
| Dot | `#E5E7EB` | grid dot on a 40 px tile |
| Label grey | `#6B7280` | eyebrows, keys |
| Meta grey | `#9CA3AF` | credit line, meta |
| Accent | `#2563EB` | the one thing that matters: links, the hero bar, arrows |
| Accent tint | `#DBEAFE` | title marker, focus rings, highlights |

The paper never changes colour. One accent per idea.

### Card tints (fill / text)
| Card | Fill | Meaning |
|---|---|---|
| Plain | `#FFFFFF` | neutral |
| Blue | `#EFF6FF` | a tool or a model |
| Green | `#D1FAE5` | good, what we keep |
| Violet | `#EDE9FE` | identity, what we swap |
| Rose | `#FFE4E6` | problems, misses |
| Solid blue | `#2563EB` | the answer, white text |
| Code | `#111827` | a command or prompt, text `#D1FAE5` |

### Signals
| Signal | Hex |
|---|---|
| ✓ works | `#059669` |
| ~ partial | `#D97706` |
| ✕ wrong | `#E11D48` |
| lost / frozen | `#EF4444` |

Never black text on a dark fill. On dark panels use white or the light tints.

## Type: Inter, JetBrains Mono, one serif aside

Load:
`https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&family=Instrument+Serif:ital@1&display=swap`

- **Inter 700/600**: titles, cards, stickers, captions.
- **JetBrains Mono 500**: tags, stamps, eyebrows, prompts, tables.
- **Instrument Serif italic**: one handwritten-style aside per board.
- Every readable word at 28 px or more. Only the credit line and a full-screen prompt go smaller.

| Role | Face | Size / line-height | Tracking |
|---|---|---|---|
| Title | Inter 700 | 76 / 1.08 | −.035em (68 for long lines) |
| Card | Inter 700 | 48 / 1.08 | 0 |
| Sticker | Inter 700 | 54 / 1 | −.02em |
| Line text | Inter 700 | 34 / 1.2 | 0 |
| Caption | Inter 700 | 28 | 0 |
| Aside | Instrument Serif italic | 58 / 1.12 | 0 |
| Tag | JetBrains Mono 500 | 36 / 1.08 | 0 |
| Eyebrow | JetBrains Mono 500 | 24 | .07em caps |
| Prompt | JetBrains Mono 500 | 21 / 1.38 | only inside a full panel |
| Credit | Inter 700 | 18 / 30 | `#9CA3AF`, bottom-left |

Big number 200 px, KPI value 110, chapter number 220 (mono), quote 96, end sign-off 128.

## Shape and elevation: soft shadows, thin borders

| Element | Spec |
|---|---|
| Card | border 1.5 px `#E5E7EB` · radius 16–22 · shadow `0 10px 30px rgba(17,24,39,.10)` |
| Footage tile | radius 12 · same soft shadow · never cropped |
| Sticker | radius 20 · 5 px white ring + soft shadow |
| Focus ring | `0 0 0 8px #DBEAFE` |
| Loss ring | `0 0 0 8px #EF4444` |

One shadow for everything. Elevation comes from scale and the accent, not from harder shadows.

## Easing

GSAP eases, with CSS equivalents:
- `power3.out` ≈ `cubic-bezier(.22,1,.36,1)`
- `back.out(1.5)` ≈ `cubic-bezier(.34,1.56,.64,1)`
- `power3.inOut` ≈ `cubic-bezier(.65,0,.35,1)`

Durations and moves are in `motion.md`.
