# Trust Scorer v2 — hand validation

Ten real `(facility × capability)` cases from the live share, checked by hand against the
raw record. This is how we defend the score to the jury: every call is grounded in the
exact sentences the record actually contains.

Rebuild: `./scripts/dbsql.sh "$(< pipeline/build_facility_trust.sql)"` (or `DB_WAREHOUSE_ID=<id>` +
the polling runner). Snapshot the previous table first if you want a v1↔v2 diff.

## Aggregate effect of v2 (vs v1 keyword-only scorer)

| Metric | v1 | v2 |
|---|---|---|
| Rows (facility×capability) | 29,054 | 29,047 |
| CORROBORATED | 3,555 | 7,505 |
| CLAIMED_ONLY | 25,496 | 21,539 |
| Pairs dropped (aspirational/negation only) | — | 7 |
| Pairs flagged "also has planned/under-construction wording" | — | 32 |

v1 was *over-strict* (it effectively required specific equipment or 3 raw fields), yet it
also *over-counted* corroboration by treating a claim copied into two fields as two
independent sources. v2 fixes both: it rewards genuine cross-source agreement and refuses
to be fooled by self-referential narrative or by aspirational wording.

## A. Aspirational / negated claims correctly DROPPED

These matched a capability keyword in v1 and were scored as real. v2 detects the
future/negation intent and removes the (facility, capability) pair entirely — the facility
does **not** actually offer the capability today.

| Facility | Capability | The sentence | Why dropped |
|---|---|---|---|
| Ankur Hospital | nicu | "NICU facility **not available**" | explicit negation |
| Shifa Hospital, Siddhpur | dialysis | "Dialysis room **(under construction)**" | not operational |
| Sri Venkateswara IMS, Tirupati | icu | "**Plans to add** five ICUs" | future intent |
| SCB Medical College, Cuttack | trauma | "A multi-specialty trauma center is **under construction**" | not operational |
| Tinsukia Medical College | oncology | "**Proposed** Cancer Hospital outside premises…" | proposed only |
| Sanjay Gandhi Memorial Hospital | trauma | "…**upcoming** Trauma Centre block" | future intent |
| Satish Nursing Home | dialysis | "…and an **upcoming dialysis wing**" | future (facility still shows for its real icu/nicu/maternity) |

**Precision guard:** "planned" alone is NOT a trigger — elective care such as
*"Performs planned surgeries"* and *"planned emergency treatment"* stays fully counted.
Aspirational detection fires only on multi-word future intent (`plans to`, `under
construction`, `proposed`, `upcoming`, `will be`, `to be established`…) or when the trigger
sits directly before the matched keyword.

## B. Fake corroboration correctly DOWNGRADED to CLAIMED_ONLY

The same self-reported claim appearing in both `capability` and `description` is one source,
not two. v2 collapses `capability`/`description`/`specialties` into a single **narrative**
bucket, so narrative-only claims can no longer reach CORROBORATED.

| Facility | Capability | v1 | v2 | Evidence |
|---|---|---|---|---|
| Alok Nursing Home & Fracture Clinic | maternity | CORROBORATED 0.62 | **CLAIMED_ONLY 0.42** | "Provides orthopaedic, gynecology…" (capability) ≈ "Provide orthopadic, gynecology…" (description) — same claim, typo apart |
| Apex Hospital | emergency | CORROBORATED 0.62 | **CLAIMED_ONLY 0.42** | "Provides 24/7 emergency…" (capability) ≈ "…operates 24/7 for emergency…" (description) |

## C. Genuine corroboration correctly KEPT

Independent buckets really agree (structured equipment/procedure + narrative), so these stay
CORROBORATED with visible receipts.

| Facility | Capability | Score | Independent buckets |
|---|---|---|---|
| Prime Care Nursing Home | surgery | 0.80 | equipment ("two modular operating theatres, laparoscopy/laser") + procedure ("gallbladder stone surgery", "humerus fracture surgery") |
| Gouri Devi IMS & Hospital | surgery | 0.80 | equipment ("10 major + 2 minor operating theatres") + procedure ("endoscopic skull base / pituitary surgery") |
| Dr Hedgewar Hospital | dialysis | 0.64 | procedure ("haemodialysis and peritoneal dialysis, incl. bedside ICU dialysis") + narrative + specialty nephrology |
| Mission Hospital, Nagercoil | maternity | 0.64 | equipment ("maternity and labour ward") + narrative (child-care history) |

## Known residual limitations (honest disclosure — future work)

- **Paraphrase de-dup is exact-key only.** Near-duplicate narrative across fields is handled
  by the bucket collapse, but two paraphrased sentences *within the same bucket* still count
  as separate evidence volume (small effect: volume is only a 0.20-weighted bonus).
- **Cross-facility duplicated text** (identical sentence credited to two different
  facilities — observed in the data) is not yet flagged. This is the job of the A2 validator
  (`feat/a-validator`), which audits the scorer's own output.
- **Follow-on negation** ("ICU is not functional") is missed when the negation trails the
  keyword; only leading/adjacent negation and unambiguous phrases are caught.
