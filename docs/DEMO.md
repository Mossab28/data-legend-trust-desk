# Demo script — 60 seconds

> One rehearsed take. Open the app BEFORE speaking (tab already loaded, sidebar
> name filled: "A. Sharma", scenario: "Maternity push — Rajasthan Q3").

**[0–10s] The problem.**
"In India, a hospital's ICU is often a claim, not a capability — and a wrong
referral is a family driving six hours for nothing. We built the trust layer
that separates the two."

**[10–25s] The core loop.** *(Find facilities → ICU → Rajasthan)*
"A planner picks a need and a region. Every facility is ranked by evidence,
not keywords: green means two independent sources agree — structured equipment,
procedures — amber means the facility only says so, and gray means we honestly
don't know. Same text copied twice never counts as proof, and 'proposed ICU'
counts as nothing."

**[25–40s] The receipts.** *(expand one corroborated facility)*
"Every verdict shows its receipts: the exact sentences from the record, field
by field — and what we still don't know. If a field worker disagrees, they
override it with a signed note, and that decision is saved for the whole team."
*(save an override live)*

**[40–52s] Deserts.** *(Medical deserts tab)*
"At district level we join the official NFHS-5 health survey: solid red means
real unmet need; hollow gray means our data is empty there — a data desert is
not a medical desert, and the app never confuses the two."

**[52–60s] Close.**
"Rule-based, fully auditable scoring — LLM extraction upstream, humans in
charge downstream — live on Databricks Free Edition, Apps + serverless SQL.
That's how 10,000 messy records become decisions a planner can defend."

## Backup answers (likely jury questions)

- **"Why no trained model?"** No ground truth exists to train or evaluate
  against. A transparent rule engine is auditable sentence by sentence — and
  the human override loop generates the labels a future model would need.
- **"How do you know the scorer is right?"** pipeline/VALIDATION.md: 10
  hand-checked cases (dropped aspirational claims, downgraded fake
  corroboration, kept genuine corroboration) + known limitations disclosed.
- **"What's Databricks-native here?"** Apps (this UI), serverless SQL
  warehouse (all queries), Delta tables (scores + persisted planner actions),
  Delta Sharing (source data), pincode + NFHS-5 joins in-platform.
- **"What would you do next?"** Cross-facility duplicated-text validator,
  MLflow tracing of the pipeline, vector search for free-text needs,
  Lakebase for planner actions.
