# Pitch (60s) + Démo (60s)

> Texte à dire en **anglais** (jury international). *En italique : ce que TU fais
> pendant ce temps — où aller, quoi cliquer.* Répète chaque script 2× chrono en main.

---

## SCRIPT 1 — LE PITCH (60 secondes, sans l'app)

*À dire face au jury, slides ou app en fond figé. Respire, débit calme : ~150 mots.*

**[0–12s] Le problème.**
"In India, a hospital's ICU is often a claim, not a capability. Families drive
six hours to a hospital that promised intensive care — and find a locked door.
Planners don't lack data: they have ten thousand facility records. What they
lack is evidence they can act on."

**[12–30s] Ce qu'on a construit.**
"We built Facility Trust Desk: the trust layer for that data. Every capability
is treated as a claim to verify. Our engine scores each claim on independent
corroboration — structured equipment and procedures against self-reported
narrative — filters out 'proposed' and 'under construction', and attaches the
exact sentences behind every verdict."

**[30–45s] L'honnêteté comme feature.**
"And the app doubts itself, on purpose. An independent validator audits our own
scores — it overturned 378 of our own 'corroborated' ratings. Uncertainty bands
tell planners what's solid versus speculative. Empty regions are labeled
'unknown', never 'empty' — a data desert is not a medical desert."

**[45–60s] Le close.**
"Humans stay in charge: every override is signed and remembered. Built entirely
on Databricks Free Edition — Apps, serverless SQL, foundation-model embeddings,
MLflow tracing, Genie. Ten thousand messy records, turned into decisions a
planner can defend. That's how data becomes care."

---

## SCRIPT 2 — LA DÉMO (60 secondes, app en live)

*AVANT de commencer (checklist 2 min) :*
- *Ouvre l'app, connecté en admin. Sidebar : scénario = "Maternity push — Rajasthan Q3".*
- *Onglet **Find facilities** déjà ouvert, capacité **ICU**, state **Rajasthan** pré-sélectionnés.*
- *Aie 2-3 facilités déjà shortlistées dans le scénario (pour que le Decision Brief soit riche).*
- *Zoom navigateur ~110%, ferme les autres onglets, coupe les notifs.*

**[0–8s] Le hook.**
*(L'écran montre déjà la liste ICU Rajasthan avec les compteurs.)*
"This is what a planner sees: every ICU claim in Rajasthan, ranked by evidence.
Green means independently corroborated. Amber: the hospital says so — nothing
confirms it. Gray: we honestly don't know."

**[8–20s] Les reçus.**
*(Clique sur une facilité 🟢 CORROBORATED → déplie **Evidence, gaps & review**.
Choisis-en une AVEC bannière rouge du validator si possible.)*
"Every verdict shows its receipts — the exact sentences from the record, field
by field, plus what we still don't know. And look: our own validator disagrees
with this rating — the app audits itself and says so, out loud."

**[20–32s] L'humain reprend la main.**
*(Dans la même carte : formulaire override → nouveau statut + note
"Field visit May 2026 — ICU confirmed" → **Save override**.)*
"A field worker who knows better overrides the machine — signed, timestamped,
stored for the whole team. The header counts every time a human corrected this
app. We wear it as a badge."

**[32–44s] Data desert ≠ medical desert.**
*(Onglet **Medical deserts** → montre les 4 tuiles → scroll à la carte.)*
"At district level, we join the official NFHS-5 health survey. Solid red:
real unmet need, proven by external indicators. Hollow gray: our records are
just empty there. Two different colors, because 'no data' is not 'no
hospitals' — and confusing them sends help to the wrong place."

**[44–54s] La décision emportée.**
*(Onglet **Shortlist & decisions** → clique **Download decision brief (.md)**
sur le scénario préparé.)*
"When the planner is done, one click exports a Decision Brief: verdicts,
verbatim evidence, uncertainty bands, the validator's objections, and every
human override — a decision the team can defend."

**[54–60s] Le close technique.**
*(Sidebar : montre du doigt "How was this computed?" — pas besoin de cliquer.)*
"All of it live on Databricks Free Edition — and the full reasoning is one
click away, traced end-to-end in MLflow. Thank you."

---

## Variantes si le jury creuse (Q&A)

- **"Show me free-text search"** → *barre du haut, tape* `burns unit` *→ résultats
  sémantiques avec chips de confiance* — "semantic search over all ten thousand
  profiles, beyond our 8 fixed capabilities; matches are leads, not verdicts."
- **"Why no trained model?"** — "No ground truth exists to train against. A
  transparent rule engine is auditable sentence by sentence — and our override
  log is exactly the labeled data a future model needs."
- **"How do you know your scorer is right?"** — "Ten hand-validated cases in
  the repo, plus an independent validator that overturned 378 of our own
  ratings. We publish our residual limitations too."
- **"What's Databricks-native?"** — "Apps, serverless SQL, Delta Sharing,
  foundation-model embeddings via ai_query, Genie, MLflow tracing, and a
  provisioned Lakebase instance for OLTP persistence."
- **"Genie?"** → *sidebar → "Ask the data in plain English" → pose* "How many
  corroborated ICU facilities in Maharashtra?" *→ il répond ~152 avec le SQL visible.*

## Chiffres à connaître par cœur

| Chiffre | Quoi |
|---|---|
| 10,088 | facilités dans le dataset |
| 29,047 | claims (facilité × capacité) évaluées |
| 7,505 | corroborées par 2+ sources indépendantes |
| **378** | notes que NOTRE validator a renversées lui-même |
| 1,360 | facilités au GPS incompatible avec leur pincode |
| 755 | districts classés (NFHS-5 joint à 81%) |
| 35 | états normalisés (depuis 254 valeurs sales) |
