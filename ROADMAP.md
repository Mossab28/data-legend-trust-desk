# ROADMAP — Win Plan · Data Legend (Facility Trust Desk)

> Objectif : pas une démo — un **produit runnable** qui écrase les critères du jury.
> Barème : Evidence & Trust **35%** · Product Judgment **30%** · Technical Execution **25%** · Ambition **10%**.
> Stratégie : chaque heure investie doit frapper une de ces 4 lignes, priorité aux deux premières (65%).

---

## Règles de dev (les DEUX agents les respectent)

- **Branches** : `main` = toujours déployable. Feature branches : `feat/a-<slug>` (Léo) et `feat/b-<slug>` (Mossab). Jamais de commit direct sur main.
- **PRs** : chaque feature = 1 PR GitHub, description courte (quoi/pourquoi/comment tester). L'autre humain (ou son agent) merge — pas d'auto-merge de son propre PR sauf urgence démo.
- **Déploiement** : UN SEUL canal — `databricks workspace import-dir app ... && databricks apps deploy facility-trust-desk ...` **depuis main uniquement, après merge**. Owner du deploy : workstream B (Mossab — le CLI est configuré sur sa machine). A ne déploie jamais directement (évite les écrasements).
- **Contrats** : `docs/CONTRACT.md` est la loi. Toute nouvelle table/colonne = d'abord une PR sur CONTRACT.md, ensuite le code. C'est ce qui permet aux 2 agents de bosser sans se bloquer.
- **Zones exclusives** (anti-conflit) :
  - Workstream **A** possède : `pipeline/`, `geo/`, `scripts/`, `mlflow/`, tables `workspace.default.*`
  - Workstream **B** possède : `app/` (tout), `design/`, assets UI
  - Fichiers partagés (`docs/CONTRACT.md`, `README.md`, `ROADMAP.md`) : modif = PR séparée minuscule.
- **Anti-AI-slop** (UI et texte) : interdits — emojis gratuits partout, gradients violets par défaut, textes génériques ("Welcome to our amazing app"), lorem ipsum, cards à ombres exagérées, phrases creuses. Référence design : dashboards SaaS sobres et denses (froid, crédible), composants 21st.dev pour l'inspiration. Une seule famille de police, une palette restreinte (fond sombre, 1 accent), chiffres en tabular. Le produit doit ressembler à un outil métier qu'une ONG paierait, pas à une landing page.

---

## WORKSTREAM A — "Trust Engine" (Léo + agent A)

*Cible : Evidence & Trust 35% + Technical 25%. Tout ce qui est data, scoring, preuve, plomberie Databricks.*

### A1 — Scoring v2 : negation & spécificité réelle `feat/a-scoring-v2`
- Détection de négation/futur dans les claims ("proposed ICU", "under construction", "will be equipped", "no ventilator") → ces phrases ne corroborent PAS, elles contredisent.
- Pondération par source : une phrase d'`equipment` avec numéro de modèle > une phrase vague de `description`.
- Dédoublonnage des phrases quasi identiques inter-champs (sinon fausse corroboration).
- Recalcule `facility_trust`, valide sur 10 cas à la main (garder les 10 dans `pipeline/VALIDATION.md` — le jury adore).

### A2 — Self-Correction Loop (stretch goal #2 du brief) `feat/a-validator`
- Table `workspace.default.trust_validations` : règles de cohérence médicale exécutées APRÈS le scoring, qui **auditent le scoring lui-même** :
  - chirurgie corroborée sans anesthésie nulle part → flag `INCONSISTENT`
  - NICU corroboré mais 0 pédiatre/gynéco dans specialties → flag
  - capacité claimée > 1000 lits mais 0 doctors → flag
  - même phrase créditée à 2 facilités différentes (cross-facility text, on l'a VU dans les données Fortis) → flag
- L'app affiche ces flags : "⚠ Our own validator disagrees with this score because…". C'est LA réponse à "apps that double-check their own work" (critère 35%).

### A3 — Intervalles de confiance statistiques (Area of Research #1) `feat/a-uncertainty`
- Bootstrap simple sur les composantes du score → `trust_score_low`, `trust_score_high` dans la table.
- Répondre à la question ouverte du brief = points Real-Impact Bonus. Documenter la méthode en 10 lignes dans `pipeline/README.md`.

### A4 — MLflow 3 Tracing (stretch goal #1) `feat/a-mlflow` ✅ FAIT
- ✅ `mlflow/trace_pipeline.py` : rejoue le pipeline extraction → scoring → ranking-par-capability → self-validation comme spans MLflow (14 spans, un run par rebuild, tag `capability` par span de ranking). Loggé dans le workspace (`/Users/<user>/trust-engine`).
- ✅ Run compagnon avec `log_params` (politique de scoring) + `log_metrics` (counts par trust_state, avg score, largeur de bande, findings validator) → runs comparables.
- ✅ Mode `--rebuild` : exécute les builds SQL dans les spans (trace d'un vrai rebuild).
- ✅ Doc `mlflow/README.md` + hook app dans `docs/CONTRACT.md` (deep-link trace pour le bouton "How was this computed?").

### A5 — Vector Search sémantique `feat/a-vector` ✅ FAIT
- ✅ Vector Search endpoint **indisponible sur Free Edition** (aucun endpoint) → fallback assumé : embeddings foundation `databricks-gte-large-en` via `ai_query`, index précalculé 100% in-warehouse.
- ✅ `pipeline/build_semantic_index.sql` : 1 embedding de profil L2-normalisé par facilité (10 008 lignes, build ~50s) dans `workspace.default.facility_semantic`.
- ✅ `pipeline/build_semantic_function.sql` : fonction SQL `semantic_facilities(query)` → top 50 par similarité (dot product), appelable direct par l'app. Requête embarquée une seule fois (~2–3s/recherche).
- ✅ Recherche libre au-delà des 8 capacités validée ("cardiac cath lab", "IVF", "burns unit", "keyhole surgery") + overlay trust via join `facility_trust`.
- ✅ CLI démo `scripts/semantic_search.py`. Tradeoff documenté dans `docs/CONTRACT.md`.

### A6 — Lakebase pour la persistance `feat/a-lakebase`
- Le brief cite Lakebase explicitement (critère Technical). Migrer `planner_actions` vers une instance Lakebase (Postgres) ; garder le fallback Delta si Lakebase indispo. L'app lit/écrit via la même interface (`persistence.py` côté B — coordonner via CONTRACT).

### A7 — Génération du "Decision Brief" `feat/a-brief` ✅ FAIT
- ✅ `scripts/decision_brief.py` : pour une shortlist (`--ids` ou `--from-shortlist` depuis planner_actions), génère un rapport Markdown exportable — par facilité : verdict + bande de confiance, evidence verbatim citée (champ source), gaps, findings du validator (désaccords flaggés ⚠), overrides humains, résumé des sources (n liens / n domaines), méthodologie + lien trace MLflow.
- ✅ Testé sur 3 facilités ICU réelles (Rela, Bankers Heart, CMC Ludhiana) → brief propre 3.7k chars.
- ✅ Fonction importable `build_brief(ids, capability, planner, host)` pour l'app (hook documenté dans `docs/CONTRACT.md`). Dégrade proprement si `planner_actions` absent.

---

## WORKSTREAM B — "Product Surface" (Mossab + agent B)

*Cible : Product Judgment 30% + Ambition 10%. Tout ce qui est UI, parcours, carte, narration démo.*

### B1 — Refonte UI anti-slop `feat/b-ui-system`
- Un thème Streamlit custom (config.toml + CSS injecté) : palette sombre sobre (1 accent, ex. ambre ou cyan désaturé), Inter ou IBM Plex, densité dashboard pro, zéro emoji décoratif (les 3 badges de confiance deviennent des pastilles CSS colorées + texte).
- Header produit : nom, one-liner, et un bandeau discret "10,088 facilities · 35 states · data = claims, not facts".
- Cards facilité redessinées : ligne compacte (nom, ville, badge, score en barre fine, n_fields), détails au clic. Densité > décoration.

### B2 — Parcours planner complet `feat/b-journey`
- État vide soigné à l'ouverture (que faire, en 3 étapes).
- Identité planner persistante (st.session_state + champ en sidebar une seule fois, plus de "your name" répété dans chaque form).
- Scénarios nommés : une shortlist = un "Planning scenario" avec titre ("Maternity push — Rajasthan Q3"), notes, export.
- Filtres qui comptent : tri par score/complétude, toggle "corroborated only", indicateur "X% of records in this region are data-sparse".

### B3 — Carte de crise digne du stretch #3 `feat/b-crisis-map`
- Vue carte India plein écran (pydeck) : chaque district de `district_coverage` coloré par `desert_class` (rouge=underserved, orange=data desert, gris=no data, vert=covered), points facilités par-dessus.
- LA règle visuelle du brief : "no hospitals here" ≠ "we don't know what's here" → 2 rendus distincts (rouge plein vs hachuré/gris).
- Tooltip district : n_facilities, indicateurs NFHS clés.

### B4 — L'écran "Why trust this?" `feat/b-evidence-ux`
- Dans le détail facilité : timeline visuelle extraction → scoring → validation (données de A2/A4), chaque étape avec sa donnée. Le jury voit les receipts sans ouvrir MLflow.
- Diff visuel quand un humain a overridé : "machine said X, [name] said Y because…".

### B5 — Recherche libre (avec A5) `feat/b-search`
- Barre de recherche naturelle en haut ("dialysis near Jaipur") branchée sur la fonction sémantique de A5, avec fallback keywords. Résultats dans la même UI de ranking.

### B6 — Démo & narration `feat/b-demo`
- `docs/DEMO.md` : script 60 secondes chronométré — (1) le problème en 1 phrase, (2) parcours Trust Desk sur un cas réel frappant (facilité claimed-only vs corroborated dans la même ville), (3) override humain persisté, (4) carte deserts, (5) "et l'app se contredit elle-même quand il faut" (validator A2).
- Screenshots + GIF dans le README. Vidéo backup enregistrée (si le wifi du hackathon meurt).

---

## Séquencement conseillé (chaque bloc = mergeable seul)

| Ordre | A (Léo) | B (Mossab) |
|---|---|---|
| 1 | A1 scoring v2 | B1 UI system |
| 2 | A2 validator | B2 journey |
| 3 | A4 MLflow | B3 crisis map |
| 4 | A6 Lakebase | B4 evidence UX |
| 5 | A5 vector | B5 search (dépend A5) |
| 6 | A3 intervalles | B6 démo |
| 7 | A7 brief | — polish final |

**Points de synchro obligatoires** (10 min, humains) : après la ligne 2 (le validator change ce que l'UI affiche), après la ligne 4 (persistance migrée), avant la démo.

## Definition of Done (avant soumission)
- [ ] App déployée depuis main, testée E2E au clic (pas juste "ça compile")
- [ ] Chaque claim affiché a sa citation visible en ≤ 2 clics
- [ ] UNKNOWN jamais présenté comme négatif, deserts jamais confondus
- [ ] README : archi (schéma), tradeoffs assumés, lien app, screenshots
- [ ] Démo 60s répétée 2× en vrai
- [ ] Repo propre : pas de secrets, pas de fichiers morts, branches mergées
