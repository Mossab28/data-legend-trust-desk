# Data Legend — Facility Trust Desk

> Databricks × Hack-Nation · Challenge 04 · Building the Trust Layer for Indian Healthcare

A live **Databricks App** (Free Edition) that turns 10,000 messy Indian healthcare-facility
records into decisions a non-technical NGO planner can **trust, defend, and save**.

**Track:** Facility Trust Desk — *"Can this facility actually do what it claims?"*

## The problem

In India, a hospital can *claim* it has an ICU, a neonatal bed, or a trauma surgeon — the
dataset is full of such claims, with **no ground truth** to verify them. This app treats every
extracted field as a **noisy claim, not a fact**, scores how much corroborating evidence backs
each claim, and is honest about what it does *not* know.

Two distinctions drive everything:

- **Claim ≠ Fact** — `capability = "ICU"` is an assertion to verify, not the truth.
- **Data desert ≠ Medical desert** — "no data here" is not "no hospitals here."

## Minimum workflow

Planner selects a capability (ICU, maternity, emergency, oncology, trauma, NICU) and a region →
sees facilities ranked with **trust signals** → expands any facility to inspect the **exact
citations** → **overrides** the assessment with a note (persisted).

## Trust score (design)

Each facility's claim is scored on corroborating evidence across fields (description, capability,
procedure, equipment, doctor counts), penalized for contradictions (e.g. "Advanced Surgery" with
no anesthesiologist listed) and for sparsity. Every score shows its receipts: the sentences that
support it and the gaps that weaken it.

## Stack (Databricks Free Edition)

| Layer | Tool |
|---|---|
| App surface | Databricks Apps |
| Extraction / reasoning | Agent Bricks + Genie |
| Retrieval (10k rows) | Mosaic AI Vector Search |
| Persistence (notes, overrides) | Lakebase |
| Observability / traceability | MLflow 3 Tracing |

## Status

🚧 Work in progress — 6th Global AI Hackathon.

## License

MIT
