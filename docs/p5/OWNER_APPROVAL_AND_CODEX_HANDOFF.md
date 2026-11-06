# P5 owner decisions and Codex handoff anchor — 2026-11-05

**Scope:** Owner-approved P5 implementation preparation. This file records instructions explicitly given in the Main Managing Chat; it does not pretend to be a cryptographic signature or replace the immutable `DECISIONS.md` / G3 governance pin.

## Owner approvals (effective)
- P5 Design Pack **v0.2a**: REVIEW PASS / APPROVED.
- P5 versioned P-B supplement **v0.2b**: APPROVED.
- P5-Q01–Q08: APPROVED within v0.2a and subsequent owner conditions.
- CR-P5-001: APPROVED, restricted to the six-column P-B output; P-B-local ordered-five-column interpretation of PB-AC-002 without modifying general `sequence_equals`; DQ-022 3×6 plus 18 cells; PB-AC-007 binding only with NEW immutable SpecVersion and exact REAL local-user Approval; only `RESULT_XLSX` in P-B production; P0 unchanged.
- **P5 Gate A: CLOSED / PASS**.
- **P5 implementation: APPROVED_TO_START** on this branch.
- **CR-P5-002: APPROVED** by owner on 2026-11-05. Adopt the full narrowly scoped phase-aware regression protocol described below.
- P5 Gate B: NOT_STARTED; merge to `main`, Gate B closure and P6 remain NOT_AUTHORIZED.

## Authoritative baseline
- Start commit / pre-implementation main: `fd39aa1bed480313504ae8b1f76e77e170cb72ba`.
- Branch: `feature/p5-export-deterministic-qa`.
- Only work under the approved Streamlit / one Python application / SQLite / local filesystem architecture; deterministic QA is mandatory, no LLM, no exchange automation.
- P0–P4 production/test/schemas/migrations, `DECISIONS.md` and G3 pin must remain unchanged. Do not weaken historical audits or silently add dependencies.
- Archive source headings and `PROPOSED` labels are preserved for historical traceability; the owner dispositions above supersede those labels **only within the exact approved bounds**.

## DESIGN PACK IS NOT STORED IN THIS REPOSITORY
Codex **must be explicitly given the separate upload** `P5_Codex_Implementation_Handoff_2026-11-05.zip` from the user. Do not invent missing docs, assume ChatGPT chat attachments are visible, or start implementation if the approved archive cannot be read.

The handoff archive includes these original unmodified packets:
- `P5_Implementation_Design_Pack_v0.2a_candidate.zip` SHA256 `a351fb55c5ea3d442cc3ff3e3facc7a09c426569aad476fb713f8f09f10ca3ac`
- `P5_Gate_A_PB_Supplement_v0.2b_candidate.zip` SHA256 `4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18`
- CR-P5-001 and CR-P5-002 original proposal texts (owner-approved status is recorded here, not retroactively altered in originals).
- Owner authorization and complete implementation instructions, manifest, and approved Product Specification v0.1 and Implementation Scope v1.1.

## Mandatory phase-aware Gate B protocol — approved CR-P5-002
1. Run **212/212 original P1–P4 tests unchanged** on isolated immutable baseline `fd39aa1bed480313504ae8b1f76e77e170cb72ba`. Record exact commit/tree, commands and JUnit.
2. Separately run ALL historical tests on the actual P5 tree. Any old scope-only failures due exclusively to approved P5 paths/UI are labeled `EXPECTED_HISTORICAL_SCOPE_CONFLICT` with exact test IDs/assertions — **never PASS, skip or xfail**. Other behavioral regressions block.
3. Run a NEW independent successor P5 integrated whole-application scope audit on the P5 tree, preserving P0–P4 byte-identical protected sources/fixtures/tests and checking finite owner-reviewed P5 additions plus minimal explicit Streamlit UI integration. Include positive and negative mutations.
4. Execute **P5-T01–T76**, no fail/error/skip/xfail, full P0 schema verification, exact P-A/B/D fixtures, approved-access P-C only, fault/restart/idempotency, both **CSV and XLSX 100000×200** successful stress with approved bounds.
5. Report three separate counts: baseline historical P1–P4, integrated P5-tree legacy compatibility, integrated P5 tests. No fictional integrated 288/288 PASS.
6. Keep P0–P4 and governance pins immutable. Any necessity to change a frozen policy needs its own explicitly approved CR, not an implicit test workaround.

## Current restrictions
- No autonomous launch of arbitrary LLM-produced code, no unapproved operation, network ingestion, marketplace actions or P6.
- No merge to main, no Gate B closure, no PR publication as integrated until owner review.
- Test-only P-B Approval is NOT real authority; do not import it into production Order state.
- Thirteen original P-C source files remain missing from current GitHub tree: do not fabricate evidence.
