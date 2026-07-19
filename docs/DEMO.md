# Pitch (60s) + Demo (60s)

> Spoken lines in **bold blocks**. *Italics: what YOU do meanwhile — where to go,
> what to click in the app.* Rehearse each script twice with a stopwatch.

---

## SCRIPT 1 — THE PITCH (60 seconds, no app)

*Delivered facing the jury, app frozen in the background. Calm pace: ~150 words.*

**[0–12s] The problem.**
"In India, a hospital's ICU is often a claim, not a capability. Families drive
six hours to a hospital that promised intensive care — and find a locked door.
Planners don't lack data: they have ten thousand facility records. What they
lack is evidence they can act on."

**[12–30s] What we built.**
"We built Facility Trust Desk: the trust layer for that data. Every capability
is treated as a claim to verify. Our engine scores each claim on independent
corroboration — structured equipment and procedures against self-reported
narrative — filters out 'proposed' and 'under construction', and attaches the
exact sentences behind every verdict."

**[30–45s] Honesty as a feature.**
"And the app doubts itself, on purpose. An independent validator audits our own
scores — it overturned 378 of our own 'corroborated' ratings. Uncertainty bands
tell planners what's solid versus speculative. Empty regions are labeled
'unknown', never 'empty' — a data desert is not a medical desert."

**[45–60s] The close.**
"Humans stay in charge: every override is signed and remembered. Built entirely
on Databricks Free Edition — Apps, serverless SQL, foundation-model embeddings,
MLflow tracing, Genie. Ten thousand messy records, turned into decisions a
planner can defend. That's how data becomes care."

---

## SCRIPT 2 — THE DEMO (60 seconds, live app)

*BEFORE you start (2-minute checklist):*
- *Open the app, signed in as admin. Sidebar: scenario = "Maternity push — Rajasthan Q3".*
- *"Find facilities" tab already open, capability **ICU**, state **Rajasthan** pre-selected.*
- *Have 2–3 facilities already shortlisted in the scenario (so the Decision Brief is rich).*
- *Browser zoom ~110%, close other tabs, mute notifications.*

**[0–8s] The hook.**
*(Screen already shows the ICU · Rajasthan list with the stat tiles.)*
"This is what a planner sees: every ICU claim in Rajasthan, ranked by evidence.
Green means independently corroborated. Amber: the hospital says so — nothing
confirms it. Gray: we honestly don't know."

**[8–20s] The receipts.**
*(Click a 🟢 CORROBORATED facility → expand **Evidence, gaps & review**.
Pick one WITH a red validator banner if possible.)*
"Every verdict shows its receipts — the exact sentences from the record, field
by field, plus what we still don't know. And look: our own validator disagrees
with this rating — the app audits itself and says so, out loud."

**[20–32s] Humans take over.**
*(In the same card: override form → new status + note
"Field visit May 2026 — ICU confirmed" → **Save override**. Keep talking while
the page reloads.)*
"A field worker who knows better overrides the machine — signed, timestamped,
stored for the whole team. The header counts every time a human corrected this
app. We wear it as a badge."

**[32–44s] Data desert ≠ medical desert.**
*(Switch to the **Medical deserts** tab → show the 4 tiles → scroll to the map.)*
"At district level, we join the official NFHS-5 health survey. Solid red:
real unmet need, proven by external indicators. Hollow gray: our records are
just empty there. Two different colors, because 'no data' is not 'no
hospitals' — and confusing them sends help to the wrong place."

**[44–54s] The decision you take home.**
*(Switch to **Shortlist & decisions** → click **Download decision brief (.md)**
on the prepared scenario.)*
"When the planner is done, one click exports a Decision Brief: verdicts,
verbatim evidence, uncertainty bands, the validator's objections, and every
human override — a decision the team can defend."

**[54–60s] The technical close.**
*(Point at "How was this computed?" in the sidebar — no need to click.)*
"All of it live on Databricks Free Edition — and the full reasoning is one
click away, traced end-to-end in MLflow. Thank you."

---

## If the jury digs deeper (Q&A moves)

- **"Show me free-text search"** → *top search bar, type* `burns unit` *→ semantic
  results with trust chips* — "semantic search over all ten thousand profiles,
  beyond our 8 fixed capabilities; matches are leads, not verdicts."
- **"Why no trained model?"** — "No ground truth exists to train against. A
  transparent rule engine is auditable sentence by sentence — and our override
  log is exactly the labeled data a future model needs."
- **"How do you know your scorer is right?"** — "Ten hand-validated cases in
  the repo, plus an independent validator that overturned 378 of our own
  ratings. We publish our residual limitations too."
- **"What's Databricks-native?"** — "Apps, serverless SQL, Delta Sharing,
  foundation-model embeddings via ai_query, Genie, MLflow tracing, and a
  provisioned Lakebase instance for OLTP persistence."
- **"Genie?"** → *sidebar → "Ask the data in plain English" → ask* "How many
  corroborated ICU facilities in Maharashtra?" *→ it answers ~152, SQL visible.*

## Numbers to know by heart

| Number | What it is |
|---|---|
| 10,088 | facilities in the dataset |
| 29,047 | claims (facility × capability) assessed |
| 7,505 | corroborated by 2+ independent sources |
| **378** | ratings OUR OWN validator overturned |
| 1,360 | facilities whose GPS contradicts their PIN code |
| 755 | districts classified (81% joined to NFHS-5) |
| 35 | normalized states (from 254 dirty values) |
