# Voiceover script — FacilityTrustDesk-Demo.mp4 (v2, 52.9s)

For ElevenLabs (or similar). **One clip per scene** is the safest way to stay in
sync: generate the 8 lines below as separate audio files, then I wire them into
the Remotion timeline at the exact start frames (they'll be mixed over the
ambient pad automatically).

Recommended ElevenLabs settings: a calm, confident narrator voice ·
stability ~50 · similarity ~75 · speed 1.0. English.

| # | Scene | Starts at | Window | Line to generate (verbatim) |
|---|---|---|---|---|
| 1 | Hook | 0.0s | 4.5s | In India, an ICU is often a claim — not a capability. |
| 2 | The data | 4.5s | 6.6s | Ten thousand facility records. Twenty-nine thousand claims. And no ground truth at all. |
| 3 | Verdicts | 10.6s | 7.5s | Facility Trust Desk gives every claim a verdict: corroborated, claimed-only, or honestly unknown — each with its own uncertainty band. |
| 4 | Receipts | 18.1s | 6.4s | Every verdict shows its receipts: the exact sentences from the record. Future promises are filtered out — intent is not capability. |
| 5 | Self-audit | 24.5s | 7.2s | And the app audits itself. Our own validator overturned three hundred and seventy-eight of our own ratings. Honesty is a feature. |
| 6 | The map | 31.7s | 7.1s | On the map of India, solid red means proven unmet need. Hollow gray means we simply don't know. A data desert is not a medical desert. |
| 7 | Override | 38.8s | 7.1s | Humans stay in charge. Every correction is signed, timestamped, and remembered for the whole team. |
| 8 | Close | 45.9s | 7.0s | Facility Trust Desk. Live on Databricks Free Edition. Decisions a planner can defend. |

## Timing notes

- "Window" = time available before the next scene's line starts. Each line as
  written fits its window at normal speaking pace (~2.4 words/sec) with a small
  breath of margin. **Don't pad the lines** — the margin is the breathing room.
- Line 5: make sure the number is spoken as "three hundred and seventy-eight"
  (write it out, as above, so the TTS doesn't rush "378").
- If a generated clip overruns its window by more than ~0.5s, regenerate with
  speed 1.05–1.1 rather than cutting words.

## Delivery back to the timeline

Name the files exactly:
`vo-1.mp3, vo-2.mp3, vo-3.mp3, vo-4.mp3, vo-5.mp3, vo-6.mp3, vo-7.mp3, vo-8.mp3`
drop them in `video/public/`, and the narration gets mixed at the start frames
above (0 / 134 / 318 / 542 / 736 / 950 / 1164 / 1378 at 30 fps), ambient pad
ducked underneath.

## Alternative: one single take

If you prefer a single continuous file, generate this paragraph and we'll align
it manually (riskier for sync):

> In India, an ICU is often a claim — not a capability. Ten thousand facility
> records. Twenty-nine thousand claims. And no ground truth at all. Facility
> Trust Desk gives every claim a verdict: corroborated, claimed-only, or
> honestly unknown — each with its own uncertainty band. Every verdict shows
> its receipts: the exact sentences from the record. Future promises are
> filtered out — intent is not capability. And the app audits itself. Our own
> validator overturned three hundred and seventy-eight of our own ratings.
> Honesty is a feature. On the map of India, solid red means proven unmet need.
> Hollow gray means we simply don't know. A data desert is not a medical
> desert. Humans stay in charge. Every correction is signed, timestamped, and
> remembered for the whole team. Facility Trust Desk. Live on Databricks Free
> Edition. Decisions a planner can defend.
