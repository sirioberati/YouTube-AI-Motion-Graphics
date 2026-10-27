# For AI agents

This repo is a toolkit for making animated explainer boards (motion graphics) for YouTube videos and syncing them to a voiceover.

- **Set it up:** follow `START-HERE.md`, then run `bash tools/setup-check.sh`.
- **Pick a board for a spoken line:** `skills/explainer-board-system/references/board-catalog.md`. Every board has "say it when" tags written in spoken words; match them against the transcript.
- **Build or restyle a board:** `skills/explainer-board-system/SKILL.md`, the tokens in `references/tokens.md`, and the rules in `checks.md`. Read `checks.md` before every build and check every frame against it.
- **Plan boards from a script:** `skills/explainer-board-brief/SKILL.md`.
- **Sync to the voice and render:** `skills/board-sync/SKILL.md`, or `tools/export.py` for a timeline JSON (Chrome renders every frame on a virtual clock, FFmpeg joins them with the audio).
- **Prompts the user may paste:** `prompts/`.
- **How it fits together:** `docs/ARCHITECTURE.md`.

Rules: boards are 1920 × 1080; keep the bottom-right camera box empty; every readable word 28 px or more; one idea per board; never invent data, logos or footage; nothing still for more than 5 seconds; never screen-record an export. When the user corrects a board, add the fix to `checks.md` as a DO or a DON'T.
