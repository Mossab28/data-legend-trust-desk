# Revue jury + checklist pré-soumission

> Évaluation objective selon les 4 critères explicites du PDF (`sujet_databricks.pdf`,
> section 6), mise à jour pour refléter l'état actuel de `main`. Sert de **checklist
> avant soumission** : ce qui est fait, et les derniers risques à fermer.

Barème jury : **Evidence & Trust 35 % · Product Judgment 30 % · Technical Execution 25 % · Ambition 10 %.**

---

## État actuel (main) — le gros du travail est intégré

Le décalage repo ↔ app livrable qui plombait la note a été résorbé : les fonctionnalités
du trust engine sont désormais **câblées et visibles dans l'app**.

| Fonctionnalité (critère) | Statut sur `main` |
|---|---|
| Citations row-level verbatim (35 %) | ✅ dans la carte facilité |
| Bannière validateur *« our own validator disagrees »* + caveats (35 %) | ✅ `app.py` |
| Bandes de confiance low→high, label solid/speculative (35 %) | ✅ `app.py` |
| Scorer v2 (buckets indépendance, négation/aspirationnel) (35 %) | ✅ pipeline mergé |
| Couche forensics/anomalies (GEO_MISMATCH, DIGITALLY_SILENT) (35 %) | ✅ onglet data-quality |
| Decision Brief exportable par scénario (30 %) | ✅ `build_brief_md` |
| Identité planner (RBAC/SSO) + scénarios nommés (30 %) | ✅ |
| *Data desert ≠ medical desert* (NFHS-5) (30 %) | ✅ onglet déserts |
| Recherche sémantique libre `semantic_facilities` (10 %) | ✅ onglet |
| « How was this computed? » deep-link MLflow (10 %) | ✅ |
| Lien Genie (10 %) | ✅ sidebar |
| Vidéo démo + pitch deck PDF + scripts | ✅ `docs/`, `video/` |

Sur le mérite, la solution est désormais dans le haut du barème. Les points restants
ci-dessous sont de la **fiabilité de démo et de reproductibilité**, pas de la conception.

---

## Risques restants à fermer avant la démo (par priorité)

### 1. 🔴 `facility_geo` n'a AUCUN script de build versionné (bloquant reproductibilité)

`app/app.py` lit `workspace.default.facility_geo` (`GEO_TABLE`, ~ligne 237) pour l'onglet
principal (états, districts) **et** les déserts. Or `geo/` ne contient que
`build_district_coverage.sql` — **pas de `build_facility_geo.sql`**.

Conséquence : sur un workspace neuf (le cas du jury / d'un re-déploiement), l'app se
lance mais **l'écran principal reste vide** (`load_states()` échoue → « facility data
isn't available »). C'est le seul trou qui peut faire échouer une démo live.

→ **Action : ajouter `geo/build_facility_geo.sql`** (normalisation `state_clean` /
`district` via l'India Post pincode directory, comme dans `build_district_coverage.sql`),
et l'inscrire dans l'ordre de build de `docs/INTEGRATION.md §0`.

### 2. 🟠 Test E2E réel depuis `main` sur le workspace de déploiement

Rebuild de toutes les tables/fonctions dans le workspace cible (ordre `INTEGRATION.md §0`),
puis **cliquer chaque parcours** : browse → citations → bande → bannière validateur →
override persisté → brief exporté → recherche sémantique → déserts. Pas juste « ça compile ».

### 3. 🟠 IDs de warehouse en dur

Vérifier que `DATABRICKS_WAREHOUSE_ID` est bien injecté par l'environnement de l'app
(`app.yaml`) et non codé en dur, pour survivre à un changement de workspace.

### 4. 🟢 Répéter la démo 60s deux fois

Choisir **un** cas frappant : deux facilités même ville, même `trust_score`, l'une
CORROBORATED l'autre CLAIMED_ONLY — idéalement une où **le validateur se contredit
lui-même**. C'est le moment qui matérialise le critère à 35 % en 15 secondes.
(Vidéo backup déjà enregistrée — bon point si le wifi meurt.)

---

## Definition of Done (avant soumission)

- [ ] `geo/build_facility_geo.sql` ajouté → repo reproductible de zéro
- [ ] Toutes les tables/fonctions rebâties dans le workspace de déploiement
- [ ] App déployée depuis `main`, testée E2E au clic (chaque parcours)
- [ ] `DATABRICKS_WAREHOUSE_ID` via env, pas en dur
- [x] Bannière validateur (`disagrees_with_score`) visible sur la carte
- [x] Bande de confiance low→high affichée
- [x] Decision Brief exportable
- [x] MLflow + recherche sémantique dans l'app
- [x] Chaque claim a sa citation en ≤ 2 clics
- [x] UNKNOWN jamais présenté comme négatif ; deserts jamais confondus
- [x] Vidéo backup enregistrée ; pitch deck prêt
- [ ] Démo 60s répétée 2× en vrai

---

## Interfaces (référence — `docs/CONTRACT.md`, `docs/INTEGRATION.md`)

- Validateur : `workspace.default.trust_validations` (`disagrees_with_score`).
- Forensics : `workspace.default.trust_anomalies` (`GEO_MISMATCH`, `DIGITALLY_SILENT`).
- Bandes : `trust_score_low` / `trust_score_high` sur `facility_trust`.
- Sémantique : `SELECT * FROM workspace.default.semantic_facilities('…')`.
- Brief CLI : `python scripts/decision_brief.py` (jumeau du `build_brief_md` in-app).
- Persistance : `scripts/persistence.py` (Lakebase primaire, Delta fallback).
- MLflow : `mlflow/trace_pipeline.py` → deep-link trace.
